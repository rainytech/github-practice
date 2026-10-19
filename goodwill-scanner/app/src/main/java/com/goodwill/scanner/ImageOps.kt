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
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

object ImageOps {
    /** Longest side kept for stored pages (about 300 dpi for A4 width). */
    const val MAX_SIDE = 2480

    fun decode(context: Context, uri: Uri, maxSide: Int = MAX_SIDE): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
        val opts = BitmapFactory.Options().apply { inSampleSize = sample }
        val bmp = context.contentResolver.openInputStream(uri)
            ?.use { BitmapFactory.decodeStream(it, null, opts) } ?: return null
        return fit(bmp, maxSide)
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

    /** A landscape capture of an open book becomes left page then right page. */
    fun splitSpread(b: Bitmap): List<Bitmap> {
        if (b.width <= b.height) return listOf(b)
        val half = b.width / 2
        return listOf(
            Bitmap.createBitmap(b, 0, 0, half, b.height),
            Bitmap.createBitmap(b, half, 0, b.width - half, b.height),
        )
    }

    fun rotate(b: Bitmap, degrees: Int): Bitmap {
        if (degrees % 360 == 0) return b
        val m = Matrix().apply { postRotate(degrees.toFloat()) }
        return Bitmap.createBitmap(b, 0, 0, b.width, b.height, m, true)
    }

    fun applyFilter(b: Bitmap, filter: PageFilter): Bitmap = when (filter) {
        PageFilter.ORIGINAL -> b
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
        val px = IntArray(w * h)
        b.getPixels(px, 0, w, 0, 0, w, h)
        for (i in px.indices) {
            val c = px[i]
            px[i] = (((c shr 16) and 0xFF) * 77 + ((c shr 8) and 0xFF) * 150 + (c and 0xFF) * 29) shr 8
        }
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

    fun saveJpeg(b: Bitmap, file: File, quality: Int = 90) {
        FileOutputStream(file).use { b.compress(Bitmap.CompressFormat.JPEG, quality, it) }
    }
}
