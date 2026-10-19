package com.goodwill.scanner

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

enum class PageFilter(val label: String) {
    ORIGINAL("Original"),
    CLEAN("Clean text"),
    MAGIC("Magic colour"),
    GREY("Greyscale"),
    BW("B & W"),
}

/** Crop rectangle as fractions (0..1) of the image width and height. */
data class CropBox(val l: Float, val t: Float, val r: Float, val b: Float) {
    /** Maps a box drawn on an already-cropped image back onto the full image. */
    fun inside(outer: CropBox?) = if (outer == null) this else CropBox(
        outer.l + l * (outer.r - outer.l), outer.t + t * (outer.b - outer.t),
        outer.l + r * (outer.r - outer.l), outer.t + b * (outer.b - outer.t),
    )
}

/** [original] is never modified; [file] is what is shown and exported. */
data class Page(
    val original: String,
    val file: String,
    val filter: PageFilter = PageFilter.ORIGINAL,
    val rotation: Int = 0,
    val crop: CropBox? = null,
    val trim: Boolean = false,
)

data class ScanDoc(
    val id: String,
    val name: String,
    val folder: String,
    val created: Long,
    val pages: List<Page>,
    val dir: File,
) {
    fun fileOf(page: Page) = File(dir, page.file)
}

class Repository(context: Context) {
    private val context = context.applicationContext
    private val root = File(context.filesDir, "docs").apply { mkdirs() }
    private val foldersFile = File(context.filesDir, "folders.json")

    fun loadAll(): List<ScanDoc> =
        root.listFiles().orEmpty()
            .filter { it.isDirectory }
            .mapNotNull { read(it) }
            .sortedByDescending { it.created }

    fun load(id: String): ScanDoc? = read(File(root, id))

    private fun read(dir: File): ScanDoc? = runCatching {
        val json = JSONObject(File(dir, "meta.json").readText())
        val arr = json.getJSONArray("pages")
        val pages = (0 until arr.length()).map { i ->
            val p = arr.getJSONObject(i)
            Page(
                original = p.getString("original"),
                file = p.getString("file"),
                filter = runCatching { PageFilter.valueOf(p.optString("filter")) }
                    .getOrDefault(PageFilter.ORIGINAL),
                rotation = p.optInt("rotation", 0),
                trim = p.optBoolean("trim", false),
                crop = p.optJSONArray("crop")?.let {
                    CropBox(it.getDouble(0).toFloat(), it.getDouble(1).toFloat(),
                        it.getDouble(2).toFloat(), it.getDouble(3).toFloat())
                },
            )
        }
        ScanDoc(dir.name, json.getString("name"), json.optString("folder", ""),
            json.getLong("created"), pages, dir)
    }.getOrNull()

    fun save(doc: ScanDoc) {
        val pages = JSONArray()
        doc.pages.forEach {
            val page = JSONObject()
                .put("original", it.original)
                .put("file", it.file)
                .put("filter", it.filter.name)
                .put("rotation", it.rotation)
                .put("trim", it.trim)
            it.crop?.let { c ->
                page.put("crop", JSONArray().put(c.l.toDouble()).put(c.t.toDouble()).put(c.r.toDouble()).put(c.b.toDouble()))
            }
            pages.put(page)
        }
        val json = JSONObject()
            .put("name", doc.name)
            .put("folder", doc.folder)
            .put("created", doc.created)
            .put("pages", pages)
        val tmp = File(doc.dir, "meta.json.tmp")
        tmp.writeText(json.toString())
        tmp.renameTo(File(doc.dir, "meta.json"))
    }

    fun create(name: String, folder: String): ScanDoc {
        val now = System.currentTimeMillis()
        val dir = File(root, "doc_${now}_${UUID.randomUUID().toString().take(6)}").apply { mkdirs() }
        return ScanDoc(dir.name, name, folder, now, emptyList(), dir).also(::save)
    }

    fun update(id: String, change: (ScanDoc) -> ScanDoc): ScanDoc? =
        load(id)?.let(change)?.also(::save)

    fun delete(id: String) = File(root, id).deleteRecursively()

    /**
     * Copies scanner output into app storage; book mode splits landscape spreads in two.
     * [filter] is applied straight away (the original is still kept).
     */
    fun addPages(doc: ScanDoc, uris: List<Uri>, bookMode: Boolean, filter: PageFilter, trim: Boolean): ScanDoc {
        val added = mutableListOf<Page>()
        for (uri in uris) {
            val bmp = ImageOps.decode(context, uri) ?: continue
            val parts = if (bookMode) ImageOps.splitSpread(bmp) else listOf(bmp)
            for (part in parts) {
                val original = "orig_${UUID.randomUUID()}.jpg"
                ImageOps.saveJpeg(part, File(doc.dir, original))
                added += render(doc.dir, Page(original, original, filter, trim = trim), part)
                if (part !== bmp) part.recycle()
            }
            bmp.recycle()
        }
        return doc.copy(pages = doc.pages + added).also(::save)
    }

    /**
     * Renders [page] from its untouched original: smart trim, filter, rotation, then crop.
     * [src] is the decoded original when the caller already has it.
     */
    private fun render(dir: File, page: Page, src: Bitmap? = null): Page {
        if (page.filter == PageFilter.ORIGINAL && page.rotation == 0 && page.crop == null && !page.trim) {
            return page.copy(file = page.original)
        }
        val base = src ?: BitmapFactory.decodeFile(File(dir, page.original).path) ?: return page.copy(file = page.original)
        val trimmed = if (page.trim) ImageOps.smartTrim(base) else base
        val out = ImageOps.crop(ImageOps.rotate(ImageOps.applyFilter(trimmed, page.filter), page.rotation), page.crop)
        val name = "page_${UUID.randomUUID()}.jpg"
        ImageOps.saveJpeg(out, File(dir, name))
        return page.copy(file = name)
    }

    /** Applies [change] to a page's settings and re-renders it. */
    fun renderPage(id: String, index: Int, change: (Page) -> Page): ScanDoc? {
        val doc = load(id) ?: return null
        val old = doc.pages.getOrNull(index) ?: return doc
        val wanted = change(old).let { it.copy(rotation = ((it.rotation % 360) + 360) % 360) }
        val page = render(doc.dir, wanted)
        if (old.file != old.original && old.file != page.file) deleteImage(File(doc.dir, old.file))
        return doc.copy(pages = doc.pages.toMutableList().also { it[index] = page }).also(::save)
    }

    fun deletePage(id: String, index: Int): ScanDoc? {
        val doc = load(id) ?: return null
        val page = doc.pages.getOrNull(index) ?: return doc
        deleteImage(File(doc.dir, page.file))
        deleteImage(File(doc.dir, page.original))
        return doc.copy(pages = doc.pages.filterIndexed { i, _ -> i != index }).also(::save)
    }

    fun movePage(id: String, from: Int, to: Int): ScanDoc? = update(id) { doc ->
        if (from !in doc.pages.indices || to !in doc.pages.indices) return@update doc
        val list = doc.pages.toMutableList()
        list.add(to, list.removeAt(from))
        doc.copy(pages = list)
    }

    private fun deleteImage(file: File) {
        file.delete()
        Ocr.cacheFile(file).delete()
    }

    fun loadFolders(): List<String> = runCatching {
        val arr = JSONArray(foldersFile.readText())
        (0 until arr.length()).map { arr.getString(it) }
    }.getOrDefault(emptyList())

    fun saveFolders(folders: List<String>) {
        foldersFile.writeText(JSONArray(folders.distinct()).toString())
    }
}
