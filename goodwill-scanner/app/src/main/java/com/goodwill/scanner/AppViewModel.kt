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

    fun importScan(targetId: String?, uris: List<Uri>, folder: String, onDone: (String) -> Unit) =
        work("Saving pages…", {
            val target = targetId?.let { repo.load(it) } ?: repo.create(defaultName(), folder)
            repo.addPages(target, uris, _bookMode.value).id
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

    fun editPage(id: String, index: Int, filter: PageFilter, rotation: Int) =
        work("Applying…", { repo.renderPage(id, index, filter, rotation) })

    fun deletePage(id: String, index: Int) = work("Deleting page…", { repo.deletePage(id, index) })

    fun movePage(id: String, from: Int, to: Int, onDone: () -> Unit) =
        work("Moving…", { repo.movePage(id, from, to) }, { onDone() })

    fun ocr(id: String, onDone: (String) -> Unit) = work("Reading text…", {
        val d = doc(id)
        Ocr.recognize(d.pages.map { d.fileOf(it) })
    }, onDone)

    fun exportPdf(id: String, onDone: (File) -> Unit) =
        work("Creating PDF…", { Exporter.pdf(getApplication(), doc(id)) }, onDone)

    fun exportJpgs(id: String, onDone: (List<File>) -> Unit) =
        work("Preparing images…", { Exporter.jpgs(getApplication(), doc(id)) }, onDone)

    fun exportText(id: String, onDone: (File) -> Unit) = work("Reading text…", {
        val d = doc(id)
        Exporter.text(getApplication(), d.name, Ocr.recognize(d.pages.map { d.fileOf(it) }))
    }, onDone)

    fun savePdfTo(id: String, uri: Uri) =
        work("Saving PDF…", { Exporter.copyPdfTo(getApplication(), doc(id), uri) }, { toast("PDF saved") })

    private fun defaultName() =
        "Scan " + SimpleDateFormat("d MMM yyyy, HH:mm", Locale.ENGLISH).format(Date())
}
