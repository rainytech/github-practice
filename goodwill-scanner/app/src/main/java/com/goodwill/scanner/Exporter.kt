package com.goodwill.scanner

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Paint
import android.graphics.Typeface
import android.net.Uri
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File
import java.io.OutputStream
import java.util.Locale
import kotlin.math.max
import kotlin.math.roundToInt

object Exporter {
    private const val DRIVE_PACKAGE = "com.google.android.apps.docs"

    private fun exportDir(context: Context) = File(context.cacheDir, "exports").apply { mkdirs() }

    fun safeName(name: String) =
        name.replace(Regex("[^A-Za-z0-9 ._-]"), "_").trim().ifEmpty { "scan" }

    /** Searchable PDF: each page image with an invisible OCR text layer on top. */
    suspend fun pdf(context: Context, doc: ScanDoc): File {
        val files = doc.pages.map { doc.fileOf(it) }.filter { it.exists() }
        val ocr = files.map { runCatching { Ocr.read(it) }.getOrNull() }
        val out = File(exportDir(context), safeName(doc.name) + ".pdf")
        out.outputStream().buffered().use { writePdf(files, ocr, it) }
        return out
    }

    suspend fun copyPdfTo(context: Context, doc: ScanDoc, target: Uri) {
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

    /** Page images resized for Claude / Gemini; [crop] applies to a single page. */
    fun aiImages(context: Context, doc: ScanDoc, pages: List<Page>, crop: CropBox? = null): List<File> {
        val base = safeName(doc.name)
        return pages.mapIndexed { i, p ->
            File(exportDir(context), String.format(Locale.US, "%s_ai_%02d.jpg", base, i + 1)).also {
                ImageOps.writeForAi(doc.fileOf(p), it, crop)
            }
        }
    }

    fun text(context: Context, name: String, text: String): File =
        File(exportDir(context), safeName(name) + ".txt").apply { writeText(text) }

    private fun intentFor(context: Context, files: List<File>, mime: String, text: String? = null): Intent {
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
        if (text != null) intent.putExtra(Intent.EXTRA_TEXT, text)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        return intent
    }

    fun share(context: Context, files: List<File>, mime: String) {
        if (files.isEmpty()) return
        context.startActivity(Intent.createChooser(intentFor(context, files, mime), "Share"))
    }

    /** Copies the prompt (some apps ignore shared text) and opens the share sheet to pick Claude or Gemini. */
    fun shareToAi(context: Context, files: List<File>, mime: String, prompt: String) {
        if (files.isEmpty()) return
        context.getSystemService(ClipboardManager::class.java)
            ?.setPrimaryClip(ClipData.newPlainText("Prompt", prompt))
        Toast.makeText(context, "Prompt copied. Paste it in the chat if it is not filled in.", Toast.LENGTH_LONG).show()
        context.startActivity(Intent.createChooser(intentFor(context, files, mime, prompt), "Send to AI"))
    }

    /** Opens Google Drive's own upload screen, where the folder can be chosen. */
    fun saveToDrive(context: Context, file: File) {
        val intent = intentFor(context, listOf(file), "application/pdf").setPackage(DRIVE_PACKAGE)
        try {
            context.startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(context, "Google Drive app not found", Toast.LENGTH_LONG).show()
            share(context, listOf(file), "application/pdf")
        }
    }

    /**
     * Minimal PDF writer that embeds the page JPEGs as-is (DCTDecode), so the
     * PDF stays small and keeps full scan quality, plus invisible OCR text.
     * Objects: 1 catalog, 2 page tree, 3 font, then page / image / content per page.
     */
    private fun writePdf(files: List<File>, ocr: List<OcrPage?>, stream: OutputStream) {
        val w = PdfOut(stream)
        val total = 3 + files.size * 3
        val measure = Paint().apply { typeface = Typeface.SANS_SERIF }
        w.raw("%PDF-1.4\n%âãÏÓ\n")
        w.obj(1, "<< /Type /Catalog /Pages 2 0 R >>")
        val kids = files.indices.joinToString(" ") { "${4 + it * 3} 0 R" }
        w.obj(2, "<< /Type /Pages /Kids [$kids] /Count ${files.size} >>")
        w.obj(3, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        files.forEachIndexed { i, f ->
            val pageNo = 4 + i * 3
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeFile(f.path, bounds)
            val iw = bounds.outWidth.coerceAtLeast(1)
            val ih = bounds.outHeight.coerceAtLeast(1)
            // A4 width in points; height follows the image.
            val pw = 595
            val ph = (pw.toFloat() * ih / iw).roundToInt().coerceAtLeast(1)
            w.obj(pageNo, "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 $pw $ph] " +
                "/Resources << /XObject << /Im0 ${pageNo + 1} 0 R >> /Font << /F1 3 0 R >> >> " +
                "/Contents ${pageNo + 2} 0 R >>")
            val jpeg = f.readBytes()
            w.begin(pageNo + 1)
            w.raw("<< /Type /XObject /Subtype /Image /Width $iw /Height $ih /ColorSpace /DeviceRGB " +
                "/BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.size} >>\nstream\n")
            w.bytes(jpeg)
            w.raw("\nendstream\nendobj\n")
            val content = StringBuilder("q $pw 0 0 $ph 0 0 cm /Im0 Do Q\n")
            val lines = ocr.getOrNull(i)?.lines.orEmpty().filter { it.text.isNotBlank() }
            if (lines.isNotEmpty()) {
                val s = pw.toFloat() / iw
                // Render mode 3 = invisible: selectable and searchable, but the image is what shows.
                content.append("BT 3 Tr\n")
                for (line in lines) {
                    val size = max(1f, (line.b - line.t) * s / 1.15f)
                    measure.textSize = size
                    val natural = measure.measureText(line.text).coerceAtLeast(0.1f)
                    val stretch = (100f * (line.r - line.l) * s / natural).coerceIn(10f, 500f)
                    val y = ph - line.b * s + size * 0.22f
                    content.append(String.format(Locale.US, "/F1 %.2f Tf %.1f Tz 1 0 0 1 %.2f %.2f Tm (%s) Tj\n",
                        size, stretch, line.l * s, y, pdfText(line.text)))
                }
                content.append("ET\n")
            }
            val bytes = content.toString().toByteArray(Charsets.ISO_8859_1)
            w.begin(pageNo + 2)
            w.raw("<< /Length ${bytes.size} >>\nstream\n")
            w.bytes(bytes)
            w.raw("\nendstream\nendobj\n")
        }
        val xref = w.pos
        val sb = StringBuilder("xref\n0 ${total + 1}\n0000000000 65535 f \n")
        for (n in 1..total) sb.append(String.format(Locale.US, "%010d 00000 n \n", w.offsets[n] ?: 0L))
        sb.append("trailer\n<< /Size ${total + 1} /Root 1 0 R >>\nstartxref\n$xref\n%%EOF\n")
        w.raw(sb.toString())
    }

    /** Escapes a PDF string; characters outside Latin-1 become '?'. */
    private fun pdfText(s: String) = buildString {
        for (c in s) when {
            c == '\\' || c == '(' || c == ')' -> append('\\').append(c)
            c.code in 32..126 || c.code in 160..255 -> append(c)
            else -> append('?')
        }
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
