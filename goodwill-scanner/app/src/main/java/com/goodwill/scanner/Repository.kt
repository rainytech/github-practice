package com.goodwill.scanner

import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

enum class PageFilter(val label: String) {
    ORIGINAL("Original"),
    MAGIC("Magic colour"),
    GREY("Greyscale"),
    BW("B & W"),
}

/** [original] is never modified; [file] is what is shown and exported. */
data class Page(
    val original: String,
    val file: String,
    val filter: PageFilter = PageFilter.ORIGINAL,
    val rotation: Int = 0,
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
            )
        }
        ScanDoc(dir.name, json.getString("name"), json.optString("folder", ""),
            json.getLong("created"), pages, dir)
    }.getOrNull()

    fun save(doc: ScanDoc) {
        val pages = JSONArray()
        doc.pages.forEach {
            pages.put(JSONObject()
                .put("original", it.original)
                .put("file", it.file)
                .put("filter", it.filter.name)
                .put("rotation", it.rotation))
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

    /** Copies scanner output into app storage; book mode splits landscape spreads in two. */
    fun addPages(doc: ScanDoc, uris: List<Uri>, bookMode: Boolean): ScanDoc {
        val added = mutableListOf<Page>()
        for (uri in uris) {
            val bmp = ImageOps.decode(context, uri) ?: continue
            val parts = if (bookMode) ImageOps.splitSpread(bmp) else listOf(bmp)
            for (part in parts) {
                val name = "orig_${UUID.randomUUID()}.jpg"
                ImageOps.saveJpeg(part, File(doc.dir, name))
                added += Page(name, name)
                if (part !== bmp) part.recycle()
            }
            bmp.recycle()
        }
        return doc.copy(pages = doc.pages + added).also(::save)
    }

    /** Re-renders a page from its untouched original with the given filter and rotation. */
    fun renderPage(id: String, index: Int, filter: PageFilter, rotation: Int): ScanDoc? {
        val doc = load(id) ?: return null
        val old = doc.pages.getOrNull(index) ?: return doc
        val rot = ((rotation % 360) + 360) % 360
        val page = if (filter == PageFilter.ORIGINAL && rot == 0) {
            old.copy(file = old.original, filter = filter, rotation = 0)
        } else {
            val src = BitmapFactory.decodeFile(File(doc.dir, old.original).path) ?: return doc
            val out = ImageOps.rotate(ImageOps.applyFilter(src, filter), rot)
            val name = "page_${UUID.randomUUID()}.jpg"
            ImageOps.saveJpeg(out, File(doc.dir, name))
            old.copy(file = name, filter = filter, rotation = rot)
        }
        if (old.file != old.original && old.file != page.file) File(doc.dir, old.file).delete()
        return doc.copy(pages = doc.pages.toMutableList().also { it[index] = page }).also(::save)
    }

    fun deletePage(id: String, index: Int): ScanDoc? {
        val doc = load(id) ?: return null
        val page = doc.pages.getOrNull(index) ?: return doc
        File(doc.dir, page.file).delete()
        File(doc.dir, page.original).delete()
        return doc.copy(pages = doc.pages.filterIndexed { i, _ -> i != index }).also(::save)
    }

    fun movePage(id: String, from: Int, to: Int): ScanDoc? = update(id) { doc ->
        if (from !in doc.pages.indices || to !in doc.pages.indices) return@update doc
        val list = doc.pages.toMutableList()
        list.add(to, list.removeAt(from))
        doc.copy(pages = list)
    }

    fun loadFolders(): List<String> = runCatching {
        val arr = JSONArray(foldersFile.readText())
        (0 until arr.length()).map { arr.getString(it) }
    }.getOrDefault(emptyList())

    fun saveFolders(folders: List<String>) {
        foldersFile.writeText(JSONArray(folders.distinct()).toString())
    }
}
