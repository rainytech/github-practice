package com.goodwill.scanner.ui

import android.graphics.BitmapFactory
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.goodwill.scanner.CropBox
import java.io.File
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

private enum class Handle { NONE, MOVE, L, T, R, B, TL, TR, BL, BR }

private const val MIN_SIZE = 0.05f

/** Shows [file] with a draggable crop rectangle: drag corners or edges to resize, inside to move. */
@Composable
fun CropEditor(file: File, box: CropBox, onChange: (CropBox) -> Unit, modifier: Modifier = Modifier) {
    val image = remember(file) {
        val o = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(file.path, o)
        max(1, o.outWidth) to max(1, o.outHeight)
    }
    val current by rememberUpdatedState(box)
    val change by rememberUpdatedState(onChange)
    val touch = with(LocalDensity.current) { 32.dp.toPx() }

    BoxWithConstraints(modifier) {
        val cw = constraints.maxWidth.toFloat()
        val ch = constraints.maxHeight.toFloat()
        // Same placement as ContentScale.Fit, centred.
        val scale = min(cw / image.first, ch / image.second)
        val dw = image.first * scale
        val dh = image.second * scale
        val ox = (cw - dw) / 2
        val oy = (ch - dh) / 2

        AsyncImage(model = file, contentDescription = null, contentScale = ContentScale.Fit,
            modifier = Modifier.fillMaxSize())
        Canvas(Modifier.fillMaxSize().pointerInput(dw, dh, ox, oy) {
            var handle = Handle.NONE
            detectDragGestures(
                onDragStart = { p -> handle = pick(p, current, ox, oy, dw, dh, touch) },
                onDrag = { event, d ->
                    event.consume()
                    if (handle != Handle.NONE) change(drag(current, handle, d.x / dw, d.y / dh))
                },
            )
        }) {
            val l = ox + box.l * dw
            val t = oy + box.t * dh
            val r = ox + box.r * dw
            val b = oy + box.b * dh
            val dim = Color.Black.copy(alpha = 0.55f)
            drawRect(dim, Offset.Zero, Size(size.width, t))
            drawRect(dim, Offset(0f, b), Size(size.width, size.height - b))
            drawRect(dim, Offset(0f, t), Size(l, b - t))
            drawRect(dim, Offset(r, t), Size(size.width - r, b - t))
            drawRect(Red, Offset(l, t), Size(r - l, b - t), style = Stroke(3.dp.toPx()))
            for (c in listOf(Offset(l, t), Offset(r, t), Offset(l, b), Offset(r, b))) {
                drawCircle(Color.White, 10.dp.toPx(), c)
                drawCircle(Blue, 10.dp.toPx(), c, style = Stroke(3.dp.toPx()))
            }
        }
    }
}

private fun pick(p: Offset, box: CropBox, ox: Float, oy: Float, dw: Float, dh: Float, touch: Float): Handle {
    val l = ox + box.l * dw
    val t = oy + box.t * dh
    val r = ox + box.r * dw
    val b = oy + box.b * dh
    val nl = abs(p.x - l) < touch
    val nr = abs(p.x - r) < touch
    val nt = abs(p.y - t) < touch
    val nb = abs(p.y - b) < touch
    val inX = p.x in (l - touch)..(r + touch)
    val inY = p.y in (t - touch)..(b + touch)
    return when {
        nl && nt -> Handle.TL
        nr && nt -> Handle.TR
        nl && nb -> Handle.BL
        nr && nb -> Handle.BR
        nl && inY -> Handle.L
        nr && inY -> Handle.R
        nt && inX -> Handle.T
        nb && inX -> Handle.B
        p.x in l..r && p.y in t..b -> Handle.MOVE
        else -> Handle.NONE
    }
}

private fun drag(box: CropBox, h: Handle, dx: Float, dy: Float): CropBox {
    var (l, t, r, b) = box
    if (h == Handle.MOVE) {
        val mx = dx.coerceIn(-l, 1f - r)
        val my = dy.coerceIn(-t, 1f - b)
        return CropBox(l + mx, t + my, r + mx, b + my)
    }
    if (h == Handle.L || h == Handle.TL || h == Handle.BL) l = (l + dx).coerceIn(0f, r - MIN_SIZE)
    if (h == Handle.R || h == Handle.TR || h == Handle.BR) r = (r + dx).coerceIn(l + MIN_SIZE, 1f)
    if (h == Handle.T || h == Handle.TL || h == Handle.TR) t = (t + dy).coerceIn(0f, b - MIN_SIZE)
    if (h == Handle.B || h == Handle.BL || h == Handle.BR) b = (b + dy).coerceIn(t + MIN_SIZE, 1f)
    return CropBox(l, t, r, b)
}
