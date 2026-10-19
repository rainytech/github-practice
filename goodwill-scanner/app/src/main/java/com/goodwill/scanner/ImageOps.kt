package com.goodwill.scanner

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Matrix
import android.graphics.Paint
import android.net.Uri
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToInt

object ImageOps {
    /** Longest side kept for stored pages (about 300 dpi for A4 width). */
    const val MAX_SIDE = 2480

    /** Claude scales larger images down to about this size, so AI uploads use it directly. */
    const val AI_SIDE = 1568

    fun decode(context: Context, uri: Uri, maxSide: Int = MAX_SIDE): Bitmap? =
        decode(maxSide) { context.contentResolver.openInputStream(uri) }

    fun decodeFile(file: File, maxSide: Int = MAX_SIDE): Bitmap? =
        decode(maxSide) { file.inputStream() }

    private fun decode(maxSide: Int, open: () -> InputStream?): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        open()?.use { BitmapFactory.decodeStream(it, null, bounds) }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
        val opts = BitmapFactory.Options().apply { inSampleSize = sample }
        val bmp = open()?.use { BitmapFactory.decodeStream(it, null, opts) } ?: return null
        return fit(bmp, maxSide)
    }

    /** Writes a copy of [src] sized for AI chat apps, optionally cropped. */
    fun writeForAi(src: File, out: File, box: CropBox? = null) {
        val full = decodeFile(src) ?: error("Cannot read page image")
        saveJpeg(fit(crop(full, box), AI_SIDE), out, 85)
    }

    private fun fit(b: Bitmap, maxSide: Int): Bitmap {
        val longest = max(b.width, b.height)
        if (longest <= maxSide) return b
        val s = maxSide.toFloat() / longest
        val out = Bitmap.createScaledBitmap(b,
            (b.width * s).roundToInt().coerceAtLeast(1),
            (b.height * s).roundToInt().coerceAtLeast(1), true)
        if (out !== b) b.recycle()
        return out
    }

    private fun analysis(b: Bitmap): Triple<IntArray, Int, Int> {
        val s = PageTrim.ANALYSIS_SIDE.toFloat() / max(b.width, b.height)
        val small = if (s >= 1f) b else Bitmap.createScaledBitmap(b,
            max(1, (b.width * s).roundToInt()), max(1, (b.height * s).roundToInt()), true)
        val px = IntArray(small.width * small.height)
        small.getPixels(px, 0, small.width, 0, 0, small.width, small.height)
        return Triple(px, small.width, small.height)
    }

    /** A landscape capture of an open book becomes left page then right page, split at the spine. */
    fun splitSpread(b: Bitmap): List<Bitmap> {
        if (b.width <= b.height) return listOf(b)
        val (px, w, h) = analysis(b)
        val at = PageTrim.findSpine(px, w, h, 0.3f, 0.7f) ?: 0.5f
        val cut = (b.width * at).roundToInt().coerceIn(1, b.width - 1)
        return listOf(
            Bitmap.createBitmap(b, 0, 0, cut, b.height),
            Bitmap.createBitmap(b, cut, 0, b.width - cut, b.height),
        )
    }

    /** Cuts off a neighbouring-page strip and paints border background (table, fingers) as paper. */
    fun smartTrim(b: Bitmap): Bitmap {
        val (px, w, h) = analysis(b)
        val (l, r) = PageTrim.sideCuts(px, w, h)
        val x0 = (l * b.width).roundToInt().coerceIn(0, b.width - 1)
        val x1 = (r * b.width).roundToInt().coerceIn(x0 + 1, b.width)
        val cut = if (x0 > 0 || x1 < b.width) Bitmap.createBitmap(b, x0, 0, x1 - x0, b.height) else b
        val (spx, sw, sh) = analysis(cut)
        val mask = PageTrim.backgroundMask(spx, sw, sh) ?: return cut
        val fill = PageTrim.paper(spx, sw, sh).color
        val cw = cut.width
        val ch = cut.height
        val out = IntArray(cw * ch)
        cut.getPixels(out, 0, cw, 0, 0, cw, ch)
        for (y in 0 until ch) {
            val row = min(y * sh / ch, sh - 1) * sw
            for (x in 0 until cw) if (mask[row + min(x * sw / cw, sw - 1)]) out[y * cw + x] = fill
        }
        return Bitmap.createBitmap(out, cw, ch, Bitmap.Config.ARGB_8888)
    }

    fun crop(b: Bitmap, box: CropBox?): Bitmap {
        if (box == null) return b
        val x = (box.l * b.width).roundToInt().coerceIn(0, b.width - 1)
        val y = (box.t * b.height).roundToInt().coerceIn(0, b.height - 1)
        val w = ((box.r - box.l) * b.width).roundToInt().coerceIn(1, b.width - x)
        val h = ((box.b - box.t) * b.height).roundToInt().coerceIn(1, b.height - y)
        return Bitmap.createBitmap(b, x, y, w, h)
    }

    fun rotate(b: Bitmap, degrees: Int): Bitmap {
        if (degrees % 360 == 0) return b
        val m = Matrix().apply { postRotate(degrees.toFloat()) }
        return Bitmap.createBitmap(b, 0, 0, b.width, b.height, m, true)
    }

    fun applyFilter(b: Bitmap, filter: PageFilter): Bitmap = when (filter) {
        PageFilter.ORIGINAL -> b
        PageFilter.CLEAN -> cleanText(b)
        PageFilter.GREY -> withMatrix(b, ColorMatrix().apply { setSaturation(0f) })
        PageFilter.MAGIC -> withMatrix(b, magic())
        PageFilter.BW -> adaptiveBw(b)
    }

    private fun magic(): ColorMatrix {
        val c = 1.35f
        val t = 128f * (1 - c) + 18f
        val contrast = ColorMatrix(floatArrayOf(
            c, 0f, 0f, 0f, t,
            0f, c, 0f, 0f, t,
            0f, 0f, c, 0f, t,
            0f, 0f, 0f, 1f, 0f,
        ))
        return ColorMatrix().apply { setSaturation(1.3f); postConcat(contrast) }
    }

    private fun withMatrix(b: Bitmap, m: ColorMatrix): Bitmap {
        val out = Bitmap.createBitmap(b.width, b.height, Bitmap.Config.ARGB_8888)
        val paint = Paint(Paint.FILTER_BITMAP_FLAG).apply { colorFilter = ColorMatrixColorFilter(m) }
        Canvas(out).drawBitmap(b, 0f, 0f, paint)
        return out
    }

    /** Local-mean threshold: removes shadows and uneven lighting, keeps text sharp. */
    private fun adaptiveBw(b: Bitmap): Bitmap {
        val w = b.width
        val h = b.height
        val px = grey(b)
        // Max sum is 255 * MAX_SIDE², which fits in an Int.
        val iw = w + 1
        val integral = IntArray(iw * (h + 1))
        for (y in 0 until h) {
            var row = 0
            for (x in 0 until w) {
                row += px[y * w + x]
                integral[(y + 1) * iw + x + 1] = integral[y * iw + x + 1] + row
            }
        }
        val r = max(8, max(w, h) / 40)
        for (y in 0 until h) {
            val y1 = max(0, y - r)
            val y2 = min(h - 1, y + r)
            for (x in 0 until w) {
                val x1 = max(0, x - r)
                val x2 = min(w - 1, x + r)
                val count = (x2 - x1 + 1) * (y2 - y1 + 1)
                val sum = integral[(y2 + 1) * iw + x2 + 1] - integral[y1 * iw + x2 + 1] -
                    integral[(y2 + 1) * iw + x1] + integral[y1 * iw + x1]
                val i = y * w + x
                px[i] = if (px[i].toLong() * count * 100 < sum.toLong() * 88) 0xFF000000.toInt() else -1
            }
        }
        return Bitmap.createBitmap(px, w, h, Bitmap.Config.ARGB_8888)
    }

    private fun grey(b: Bitmap): IntArray {
        val px = IntArray(b.width * b.height)
        b.getPixels(px, 0, b.width, 0, 0, b.width, b.height)
        for (i in px.indices) {
            val c = px[i]
            px[i] = (((c shr 16) and 0xFF) * 77 + ((c shr 8) and 0xFF) * 150 + (c and 0xFF) * 29) shr 8
        }
        return px
    }

    /**
     * Divides each pixel by the local paper brightness, which removes the
     * dark shadow near the book spine and uneven lighting, then darkens text.
     * Keeps grey edges on letters, which reads better than hard black and white.
     */
    private fun cleanText(b: Bitmap): Bitmap {
        val w = b.width
        val h = b.height
        val px = grey(b)
        // Paper estimate: brightest pixel per 8x8 block (drops thin text), then smooth.
        val cell = 8
        val sw = (w + cell - 1) / cell
        val sh = (h + cell - 1) / cell
        var paper = IntArray(sw * sh)
        for (y in 0 until h) for (x in 0 until w) {
            val i = (y / cell) * sw + x / cell
            if (px[y * w + x] > paper[i]) paper[i] = px[y * w + x]
        }
        paper = neighbourhood(paper, sw, sh, 2, useMax = true)
        paper = neighbourhood(paper, sw, sh, 3, useMax = false)
        for (y in 0 until h) {
            val fy = ((y + 0.5f) / cell - 0.5f).coerceIn(0f, (sh - 1).toFloat())
            val y0 = fy.toInt()
            val y1 = min(y0 + 1, sh - 1)
            val ty = fy - y0
            for (x in 0 until w) {
                val fx = ((x + 0.5f) / cell - 0.5f).coerceIn(0f, (sw - 1).toFloat())
                val x0 = fx.toInt()
                val x1 = min(x0 + 1, sw - 1)
                val tx = fx - x0
                val top = paper[y0 * sw + x0] * (1 - tx) + paper[y0 * sw + x1] * tx
                val bottom = paper[y1 * sw + x0] * (1 - tx) + paper[y1 * sw + x1] * tx
                val bg = max(top * (1 - ty) + bottom * ty, 1f)
                val v = px[y * w + x] * 255f / bg
                val g = if (v >= 230f) 255 else (255f * (v / 230f).pow(1.6f)).toInt().coerceIn(0, 255)
                px[y * w + x] = (0xFF shl 24) or (g shl 16) or (g shl 8) or g
            }
        }
        return Bitmap.createBitmap(px, w, h, Bitmap.Config.ARGB_8888)
    }

    /** Square max filter or mean blur of radius [r] on a small grid. */
    private fun neighbourhood(src: IntArray, w: Int, h: Int, r: Int, useMax: Boolean): IntArray {
        val out = IntArray(src.size)
        for (y in 0 until h) for (x in 0 until w) {
            var acc = 0
            var n = 0
            for (yy in max(0, y - r)..min(h - 1, y + r)) for (xx in max(0, x - r)..min(w - 1, x + r)) {
                val v = src[yy * w + xx]
                if (useMax) { if (v > acc) acc = v } else acc += v
                n++
            }
            out[y * w + x] = if (useMax) acc else acc / n
        }
        return out
    }

    fun saveJpeg(b: Bitmap, file: File, quality: Int = 90) {
        FileOutputStream(file).use { b.compress(Bitmap.CompressFormat.JPEG, quality, it) }
    }
}
