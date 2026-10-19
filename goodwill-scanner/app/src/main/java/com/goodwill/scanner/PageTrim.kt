package com.goodwill.scanner

import kotlin.math.max
import kotlin.math.min

/**
 * Finds what is not part of the scanned page, working on a small ARGB copy
 * (about 480 px). Plain Kotlin with no Android types, so it is tested off the phone.
 *
 * Two things are detected:
 *  - the book spine: a wide, soft shadow band with no print, beyond which lies
 *    the neighbouring page;
 *  - background touching the border (table, fingers, page stack): coloured or
 *    dark areas connected to the edge and thick enough not to be text or lines.
 */
object PageTrim {
    /** Long side of the analysis image. */
    const val ANALYSIS_SIDE = 480

    class Paper(val lum: Int, val sat: Int, val color: Int)

    private fun lum(c: Int) = (((c shr 16) and 0xFF) * 77 + ((c shr 8) and 0xFF) * 150 + (c and 0xFF) * 29) shr 8

    private fun sat(c: Int): Int {
        val r = (c shr 16) and 0xFF
        val g = (c shr 8) and 0xFF
        val b = c and 0xFF
        return max(r, max(g, b)) - min(r, min(g, b))
    }

    /** Paper brightness, colourfulness and colour, measured in the centre of the image. */
    fun paper(px: IntArray, w: Int, h: Int): Paper {
        val hist = IntArray(256)
        var n = 0
        for (y in h / 4 until h * 3 / 4) for (x in w / 4 until w * 3 / 4) { hist[lum(px[y * w + x])]++; n++ }
        var acc = 0
        var p90 = 255
        for (v in 0..255) { acc += hist[v]; if (acc >= n * 0.9) { p90 = v; break } }
        val sats = ArrayList<Int>()
        var r = 0L; var g = 0L; var b = 0L
        for (y in h / 4 until h * 3 / 4) for (x in w / 4 until w * 3 / 4) {
            val c = px[y * w + x]
            if (lum(c) >= p90 * 0.85) {
                sats += sat(c)
                r += (c shr 16) and 0xFF; g += (c shr 8) and 0xFF; b += c and 0xFF
            }
        }
        if (sats.isEmpty()) return Paper(max(p90, 1), 0, -1)
        sats.sort()
        val k = sats.size
        val color = (0xFF shl 24) or ((r / k).toInt() shl 16) or ((g / k).toInt() shl 8) or (b / k).toInt()
        return Paper(max(p90, 1), sats[k / 2], color)
    }

    private class Profile(val paper: FloatArray, val ink: FloatArray, val level: Float)

    /**
     * Per column, over the middle 70% of the height: paper brightness (90th
     * percentile, so print does not lower it but shadow and background do) and
     * print density measured against that column's own paper, so a shadow is
     * not mistaken for print. Both smoothed.
     */
    private fun profile(px: IntArray, w: Int, h: Int): Profile {
        val y0 = h * 15 / 100
        val y1 = max(y0 + 1, h * 85 / 100)
        val n = y1 - y0
        val paper = FloatArray(w)
        val ink = FloatArray(w)
        val hist = IntArray(256)
        for (x in 0 until w) {
            hist.fill(0)
            for (y in y0 until y1) hist[lum(px[y * w + x])]++
            var acc = 0
            var p90 = 255
            for (v in 0..255) { acc += hist[v]; if (acc >= n * 0.9) { p90 = v; break } }
            var dark = 0
            val limit = (p90 * 0.6f).toInt()
            for (v in 0 until limit) dark += hist[v]
            paper[x] = p90.toFloat()
            ink[x] = dark.toFloat() / n
        }
        val k = max(2, w / 50)
        val sm = smooth(paper, k)
        val central = sm.copyOfRange(w / 4, max(w / 4 + 1, w * 3 / 4)).sorted()
        return Profile(sm, smooth(ink, k), central[central.size / 2])
    }

    private fun smooth(a: FloatArray, r: Int) = FloatArray(a.size) { i ->
        var s = 0f
        var n = 0
        for (j in max(0, i - r)..min(a.size - 1, i + r)) { s += a[j]; n++ }
        s / n
    }

    private class Dip(val at: Int, val from: Int, val to: Int, val depth: Float)

    /** Darkest wide, print-free band between columns [from, to). */
    private fun dip(p: Profile, from: Int, to: Int, minWidth: Int): Dip? {
        if (to - from < 3) return null
        var xm = from
        for (x in from until to) if (p.paper[x] < p.paper[xm]) xm = x
        val depth = p.level - p.paper[xm]
        if (depth < p.level * 0.10f || p.ink[xm] > 0.06f) return null
        val half = p.level - depth / 2
        var l = xm
        while (l > 0 && p.paper[l - 1] < half) l--
        var r = xm
        while (r < p.paper.size - 1 && p.paper[r + 1] < half) r++
        if (r - l + 1 < minWidth) return null
        return Dip(xm, l, r, depth)
    }

    /** Spine position as a fraction of the width, searched between [from] and [to]; for splitting a spread. */
    fun findSpine(px: IntArray, w: Int, h: Int, from: Float, to: Float): Float? {
        val p = profile(px, w, h)
        val d = dip(p, (w * from).toInt(), (w * to).toInt(), max(3, w / 80)) ?: return null
        // A spine is inside the page area, not a dark band at the image edge.
        if (d.from == 0 || d.to == w - 1) return null
        return d.at.toFloat() / w
    }

    /**
     * Left and right cut for a single page: removes a strip of the neighbouring
     * page beyond the spine, or a dark band along a side edge. Never cuts into print.
     */
    fun sideCuts(px: IntArray, w: Int, h: Int): Pair<Float, Float> {
        val p = profile(px, w, h)
        val minWidth = max(3, w / 80)
        val limit = (w * 0.35f).toInt()

        fun cut(fromLeft: Boolean): Int {
            val d = (if (fromLeft) dip(p, 0, limit, minWidth) else dip(p, w - limit, w, minWidth)) ?: return 0
            val touchesEdge = if (fromLeft) d.from == 0 else d.to == w - 1
            var c = if (!touchesEdge) {
                // Spine with the neighbouring page beyond it: cut at its darkest line.
                if (fromLeft) d.at else w - 1 - d.at
            } else {
                // Dark band at the edge: cut to where it fades back towards paper.
                val back = p.level - d.depth / 4
                var x = d.at
                if (fromLeft) { while (x < w - 1 && p.paper[x] < back) x++; x } else {
                    while (x > 0 && p.paper[x] < back) x--
                    w - 1 - x
                }
            }
            // Never cut into columns that carry print on this page.
            if (touchesEdge) {
                for (i in 0 until c) {
                    val x = if (fromLeft) i else w - 1 - i
                    if (p.ink[x] > 0.04f) { c = i; break }
                }
            }
            return c.coerceIn(0, limit)
        }

        val l = cut(true)
        val r = cut(false)
        return l.toFloat() / w to (w - r).toFloat() / w
    }

    /**
     * Background connected to the border: coloured (table, skin) or dark (page stack).
     * Thin parts are dropped so text or ruled lines touching the edge stay.
     * Returns null when there is nothing to remove or the result looks unsafe.
     */
    fun backgroundMask(px: IntArray, w: Int, h: Int): BooleanArray? {
        val paper = paper(px, w, h)
        val satLimit = paper.sat + 28
        val darkLimit = paper.lum * 0.5f
        fun isBackground(i: Int): Boolean {
            val c = px[i]
            return sat(c) > satLimit || lum(c) < darkLimit
        }
        val mask = BooleanArray(w * h)
        val queue = IntArray(w * h)
        var head = 0
        var tail = 0
        fun seed(i: Int) { if (!mask[i] && isBackground(i)) { mask[i] = true; queue[tail++] = i } }
        for (x in 0 until w) { seed(x); seed((h - 1) * w + x) }
        for (y in 0 until h) { seed(y * w); seed(y * w + w - 1) }
        while (head < tail) {
            val i = queue[head++]
            val x = i % w
            val y = i / w
            if (x > 0) seed(i - 1)
            if (x < w - 1) seed(i + 1)
            if (y > 0) seed(i - w)
            if (y < h - 1) seed(i + w)
        }
        val opened = grow(shrink(mask, w, h, 2), w, h, 3)
        val count = opened.count { it }
        if (count == 0 || count > w * h * 0.4) return null
        return opened
    }

    private fun shrink(m: BooleanArray, w: Int, h: Int, r: Int) = BooleanArray(m.size) { i ->
        val x = i % w
        val y = i / w
        var all = true
        loop@ for (yy in y - r..y + r) for (xx in x - r..x + r) {
            // Outside the image counts as background, so regions at the edge survive.
            if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue
            if (!m[yy * w + xx]) { all = false; break@loop }
        }
        all
    }

    private fun grow(m: BooleanArray, w: Int, h: Int, r: Int) = BooleanArray(m.size) { i ->
        val x = i % w
        val y = i / w
        var any = false
        loop@ for (yy in max(0, y - r)..min(h - 1, y + r)) for (xx in max(0, x - r)..min(w - 1, x + r)) {
            if (m[yy * w + xx]) { any = true; break@loop }
        }
        any
    }
}
