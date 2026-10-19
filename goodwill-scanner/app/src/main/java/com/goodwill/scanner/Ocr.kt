package com.goodwill.scanner

import android.graphics.BitmapFactory
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.tasks.await
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** One recognised line with its box in image pixels. */
data class OcrLine(val text: String, val l: Int, val t: Int, val r: Int, val b: Int)

data class OcrPage(val text: String, val width: Int, val height: Int, val lines: List<OcrLine>)

object Ocr {
    private val client by lazy { TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS) }

    /** Results are cached beside each image; an edited page gets a new file name, so the cache stays valid. */
    fun cacheFile(image: File) = File(image.path + ".ocr.json")

    suspend fun read(image: File): OcrPage {
        val cache = cacheFile(image)
        if (cache.exists()) runCatching { return parse(JSONObject(cache.readText())) }
        val bmp = BitmapFactory.decodeFile(image.path) ?: return OcrPage("", 0, 0, emptyList())
        val result = client.process(InputImage.fromBitmap(bmp, 0)).await()
        val lines = result.textBlocks.flatMap { it.lines }.mapNotNull { line ->
            line.boundingBox?.let { OcrLine(line.text, it.left, it.top, it.right, it.bottom) }
        }
        val page = OcrPage(result.text, bmp.width, bmp.height, lines)
        bmp.recycle()
        cache.writeText(toJson(page).toString())
        return page
    }

    suspend fun text(files: List<File>): String =
        files.mapIndexed { i, f ->
            val text = read(f).text
            if (files.size > 1) "--- Page ${i + 1} ---\n$text" else text
        }.joinToString("\n\n").trim()

    private fun toJson(p: OcrPage): JSONObject {
        val lines = JSONArray()
        p.lines.forEach {
            lines.put(JSONObject().put("s", it.text).put("l", it.l).put("t", it.t).put("r", it.r).put("b", it.b))
        }
        return JSONObject().put("text", p.text).put("w", p.width).put("h", p.height).put("lines", lines)
    }

    private fun parse(o: JSONObject): OcrPage {
        val arr = o.getJSONArray("lines")
        val lines = (0 until arr.length()).map {
            val l = arr.getJSONObject(it)
            OcrLine(l.getString("s"), l.getInt("l"), l.getInt("t"), l.getInt("r"), l.getInt("b"))
        }
        return OcrPage(o.getString("text"), o.getInt("w"), o.getInt("h"), lines)
    }
}

/** Builds a name such as "Illustration 25 · Pg 4.32" from the first page's text. */
object Naming {
    private val question = Regex(
        """\b(illustration|question|exercise|problem|example)\s*(?:no\.?\s*)?(\d+[a-z]?)\b""",
        RegexOption.IGNORE_CASE,
    )
    private val pageNumber = Regex("""^\d{1,3}(\.\d{1,3})?$""")

    fun suggest(p: OcrPage): String? {
        val q = question.find(p.text)?.let { m ->
            m.groupValues[1].lowercase().replaceFirstChar { it.uppercase() } + " " + m.groupValues[2]
        }
        // Page numbers sit alone at the start or end of a line in the top or bottom tenth of the page.
        val band = p.height / 10
        val pg = p.lines
            .filter { it.b < band || it.t > p.height - band }
            .flatMap { line -> line.text.trim().split(Regex("\\s+")).let { listOf(it.first(), it.last()) } }
            .firstOrNull { pageNumber.matches(it) }
        return listOfNotNull(q, pg?.let { "Pg $it" }).joinToString(" · ").ifEmpty { null }
    }
}
