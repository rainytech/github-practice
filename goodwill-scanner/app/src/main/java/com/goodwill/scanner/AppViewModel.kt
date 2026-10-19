package com.goodwill.scanner

import android.app.Application
import android.content.Context
import android.net.Uri
import android.widget.Toast
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class AppViewModel(app: Application) : AndroidViewModel(app) {
    private val repo = Repository(app)
    private val prefs = app.getSharedPreferences("settings", Context.MODE_PRIVATE)

    private val _docs = MutableStateFlow<List<ScanDoc>>(emptyList())
    val docs: StateFlow<List<ScanDoc>> = _docs
    private val _folders = MutableStateFlow<List<String>>(emptyList())
    val folders: StateFlow<List<String>> = _folders
    private val _busy = MutableStateFlow<String?>(null)
    val busy: StateFlow<String?> = _busy
    private val _bookMode = MutableStateFlow(prefs.getBoolean("book_mode", false))
    val bookMode: StateFlow<Boolean> = _bookMode
    private val _autoClean = MutableStateFlow(prefs.getBoolean("auto_clean", true))
    val autoClean: StateFlow<Boolean> = _autoClean
    private val _smartTrim = MutableStateFlow(prefs.getBoolean("smart_trim", true))
    val smartTrim: StateFlow<Boolean> = _smartTrim
    private val _aiPrompt = MutableStateFlow(prefs.getString("ai_prompt", null) ?: DEFAULT_PROMPT)
    val aiPrompt: StateFlow<String> = _aiPrompt

    init {
        viewModelScope.launch(Dispatchers.IO) { reload() }
    }

    private fun reload() {
        val all = repo.loadAll()
        _docs.value = all
        _folders.value = (repo.loadFolders() + all.map { it.folder })
            .filter { it.isNotEmpty() }.distinct().sorted()
    }

    private fun toast(msg: String) =
        Toast.makeText(getApplication<Application>(), msg, Toast.LENGTH_LONG).show()

    /** Runs [block] off the main thread behind the progress dialog, then refreshes the lists. */
    private fun <T> work(msg: String, block: suspend () -> T, onDone: (T) -> Unit = {}) {
        viewModelScope.launch {
            _busy.value = msg
            try {
                val result = withContext(Dispatchers.IO) { block().also { reload() } }
                onDone(result)
            } catch (e: Throwable) {
                if (e is CancellationException) throw e
                toast(if (e is OutOfMemoryError) "Not enough memory for this page" else "Error: ${e.message}")
            } finally {
                _busy.value = null
            }
        }
    }

    private fun doc(id: String) = repo.load(id) ?: error("Document not found")

    fun setBookMode(on: Boolean) {
        _bookMode.value = on
        prefs.edit().putBoolean("book_mode", on).apply()
    }

    fun setAutoClean(on: Boolean) {
        _autoClean.value = on
        prefs.edit().putBoolean("auto_clean", on).apply()
    }

    fun setSmartTrim(on: Boolean) {
        _smartTrim.value = on
        prefs.edit().putBoolean("smart_trim", on).apply()
    }

    private fun saveAiPrompt(prompt: String) {
        _aiPrompt.value = prompt
        prefs.edit().putString("ai_prompt", prompt).apply()
    }

    fun importScan(targetId: String?, uris: List<Uri>, folder: String, onDone: (String) -> Unit) =
        work("Saving pages…", {
            val existing = targetId?.let { repo.load(it) }
            val target = existing ?: repo.create(defaultName(), folder)
            val filter = if (_autoClean.value) PageFilter.CLEAN else PageFilter.ORIGINAL
            val doc = repo.addPages(target, uris, _bookMode.value, filter, _smartTrim.value)
            if (existing == null) {
                // Name a new scan after the question and page number found on its first page.
                val first = doc.pages.firstOrNull()
                val name = first?.let { runCatching { Naming.suggest(Ocr.read(doc.fileOf(it))) }.getOrNull() }
                if (name != null) repo.update(doc.id) { it.copy(name = name) }
            }
            doc.id
        }, onDone)

    fun rename(id: String, name: String) = work("Saving…", { repo.update(id) { it.copy(name = name) } })

    fun moveToFolder(id: String, folder: String) =
        work("Saving…", { repo.update(id) { it.copy(folder = folder) } })

    fun delete(id: String) = work("Deleting…", { repo.delete(id) })

    fun addFolder(name: String) = work("Saving…", { repo.saveFolders(repo.loadFolders() + name) })

    fun deleteFolder(name: String) = work("Deleting folder…", {
        repo.saveFolders(repo.loadFolders() - name)
        repo.loadAll().filter { it.folder == name }.forEach { repo.save(it.copy(folder = "")) }
    })

    fun editPage(id: String, index: Int, change: (Page) -> Page) =
        work("Applying…", { repo.renderPage(id, index, change) })

    /** [box] is drawn on the page as currently shown, which may already be cropped. */
    fun cropPage(id: String, index: Int, box: CropBox) =
        work("Cropping…", { repo.renderPage(id, index) { it.copy(crop = box.inside(it.crop)) } })

    fun deletePage(id: String, index: Int) = work("Deleting page…", { repo.deletePage(id, index) })

    fun movePage(id: String, from: Int, to: Int, onDone: () -> Unit) =
        work("Moving…", { repo.movePage(id, from, to) }, { onDone() })

    fun ocr(id: String, onDone: (String) -> Unit) = work("Reading text…", {
        val d = doc(id)
        Ocr.text(d.pages.map { d.fileOf(it) })
    }, onDone)

    /** Prepares a whole document, one page ([pageIndex]) or a cropped part of it for an AI chat app. */
    fun sendToAi(
        id: String, pageIndex: Int?, crop: CropBox?, asPdf: Boolean, prompt: String,
        onDone: (List<File>, String) -> Unit,
    ) {
        saveAiPrompt(prompt)
        work("Preparing for AI…", {
            val d = doc(id)
            if (asPdf) listOf(Exporter.pdf(getApplication(), d)) to "application/pdf"
            else {
                val pages = if (pageIndex == null) d.pages else listOf(d.pages[pageIndex])
                Exporter.aiImages(getApplication(), d, pages, crop) to "image/jpeg"
            }
        }, { (files, mime) -> onDone(files, mime) })
    }

    fun exportPdf(id: String, onDone: (File) -> Unit) =
        work("Creating PDF…", { Exporter.pdf(getApplication(), doc(id)) }, onDone)

    fun exportJpgs(id: String, onDone: (List<File>) -> Unit) =
        work("Preparing images…", { Exporter.jpgs(getApplication(), doc(id)) }, onDone)

    fun exportText(id: String, onDone: (File) -> Unit) = work("Reading text…", {
        val d = doc(id)
        Exporter.text(getApplication(), d.name, Ocr.text(d.pages.map { d.fileOf(it) }))
    }, onDone)

    fun savePdfTo(id: String, uri: Uri) =
        work("Saving PDF…", { Exporter.copyPdfTo(getApplication(), doc(id), uri) }, { toast("PDF saved") })

    companion object {
        const val DEFAULT_PROMPT =
            "Solve the question in the attached textbook page. " +
                "Read every figure carefully from the image. " +
                "Show working notes step by step and state the final answer clearly."
    }

    private fun defaultName() =
        "Scan " + SimpleDateFormat("d MMM yyyy, HH:mm", Locale.ENGLISH).format(Date())
}
