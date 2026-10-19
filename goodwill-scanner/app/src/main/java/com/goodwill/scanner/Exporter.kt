package com.goodwill.scanner

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.core.content.FileProvider
import java.io.File
import java.io.OutputStream
import java.util.Locale
import kotlin.math.roundToInt

object Exporter {
    private fun exportDir(context: Context) = File(context.cacheDir, "exports").apply { mkdirs() }

    fun safeName(name: String) =
        name.replace(Regex("[^A-Za-z0-9 _-]"), "_").trim().ifEmpty { "scan" }

    fun pdf(context: Context, doc: ScanDoc): File {
        val out = File(exportDir(context), safeName(doc.name) + ".pdf")
        out.outputStream().buffered().use { writePdf(doc, it) }
        return out
    }

    fun copyPdfTo(context: Context, doc: ScanDoc, target: Uri) {
        val file = pdf(context, doc)
        context.contentResolver.openOutputStream(target)?.use { o ->
            file.inputStream().use { it.copyTo(o) }
        } ?: error("Cannot write to the chosen location")
    }

    fun jpgs(context: Context, doc: ScanDoc): List<File> {
        val base = safeName(doc.name)
        return doc.pages.mapIndexed { i, p ->
            val f = File(exportDir(context), String.format(Locale.US, "%s_%02d.jpg", base, i + 1))
            doc.fileOf(p).copyTo(f, overwrite = true)
        }
    }

    fun text(context: Context, name: String, text: String): File =
        File(exportDir(context), safeName(name) + ".txt").apply { writeText(text) }

    fun share(context: Context, files: List<File>, mime: String) {
        if (files.isEmpty()) return
        val uris = files.map { FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", it) }
        val intent = if (uris.size == 1) {
            Intent(Intent.ACTION_SEND).putExtra(Intent.EXTRA_STREAM, uris[0])
        } else {
            Intent(Intent.ACTION_SEND_MULTIPLE).putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(uris))
        }
        intent.type = mime
        intent.clipData = ClipData.newRawUri(null, uris[0]).apply {
            uris.drop(1).forEach { addItem(ClipData.Item(it)) }
        }
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        context.startActivity(Intent.createChooser(intent, "Share"))
    }

    /**
     * Minimal PDF writer that embeds the page JPEGs as-is (DCTDecode),
     * so the PDF stays small and keeps full scan quality.
     * Objects: 1 catalog, 2 page tree, then page / image / content per page.
     */
    private fun writePdf(doc: ScanDoc, stream: OutputStream) {
        val files = doc.pages.map { doc.fileOf(it) }.filter { it.exists() }
        val w = PdfOut(stream)
        val total = 2 + files.size * 3
        w.raw("%PDF-1.4\n%âãÏÓ\n")
        w.obj(1, "<< /Type /Catalog /Pages 2 0 R >>")
        val kids = files.indices.joinToString(" ") { "${3 + it * 3} 0 R" }
        w.obj(2, "<< /Type /Pages /Kids [$kids] /Count ${files.size} >>")
        files.forEachIndexed { i, f ->
            val pageNo = 3 + i * 3
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeFile(f.path, bounds)
            val iw = bounds.outWidth.coerceAtLeast(1)
            val ih = bounds.outHeight.coerceAtLeast(1)
            // A4 width in points; height follows the image.
            val pw = 595
            val ph = (pw.toFloat() * ih / iw).roundToInt().coerceAtLeast(1)
            w.obj(pageNo, "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 $pw $ph] " +
                "/Resources << /XObject << /Im0 ${pageNo + 1} 0 R >> >> /Contents ${pageNo + 2} 0 R >>")
            val jpeg = f.readBytes()
            w.begin(pageNo + 1)
            w.raw("<< /Type /XObject /Subtype /Image /Width $iw /Height $ih /ColorSpace /DeviceRGB " +
                "/BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.size} >>\nstream\n")
            w.bytes(jpeg)
            w.raw("\nendstream\nendobj\n")
            val content = "q $pw 0 0 $ph 0 0 cm /Im0 Do Q"
            w.obj(pageNo + 2, "<< /Length ${content.length} >>\nstream\n$content\nendstream")
        }
        val xref = w.pos
        val sb = StringBuilder("xref\n0 ${total + 1}\n0000000000 65535 f \n")
        for (n in 1..total) sb.append(String.format(Locale.US, "%010d 00000 n \n", w.offsets[n] ?: 0L))
        sb.append("trailer\n<< /Size ${total + 1} /Root 1 0 R >>\nstartxref\n$xref\n%%EOF\n")
        w.raw(sb.toString())
    }

    private class PdfOut(private val out: OutputStream) {
        var pos = 0L
        val offsets = HashMap<Int, Long>()
        fun raw(s: String) = bytes(s.toByteArray(Charsets.ISO_8859_1))
        fun bytes(b: ByteArray) { out.write(b); pos += b.size }
        fun begin(n: Int) { offsets[n] = pos; raw("$n 0 obj\n") }
        fun obj(n: Int, body: String) { begin(n); raw("$body\nendobj\n") }
    }
}
