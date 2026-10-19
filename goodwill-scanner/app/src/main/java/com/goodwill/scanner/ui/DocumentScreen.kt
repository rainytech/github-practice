@file:OptIn(ExperimentalMaterial3Api::class)

package com.goodwill.scanner.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.goodwill.scanner.AppViewModel
import com.goodwill.scanner.Exporter

@Composable
fun DocumentScreen(vm: AppViewModel, id: String, onBack: () -> Unit, onPage: (Int) -> Unit) {
    val docs by vm.docs.collectAsState()
    val folders by vm.folders.collectAsState()
    val doc = docs.find { it.id == id }
    if (doc == null) {
        LaunchedEffect(Unit) { onBack() }
        return
    }
    val context = LocalContext.current
    var menu by remember { mutableStateOf(false) }
    var shareMenu by remember { mutableStateOf(false) }
    var rename by remember { mutableStateOf(false) }
    var move by remember { mutableStateOf(false) }
    var delete by remember { mutableStateOf(false) }
    var ocrText by remember { mutableStateOf<String?>(null) }
    var aiDialog by remember { mutableStateOf(false) }
    val aiPrompt by vm.aiPrompt.collectAsState()
    val scan = rememberScanner { uris -> vm.importScan(id, uris, doc.folder) {} }
    val savePdf = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { uri ->
        if (uri != null) vm.savePdfTo(id, uri)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(doc.name, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                colors = barColors(),
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") }
                },
                actions = {
                    Box {
                        IconButton(onClick = { shareMenu = true }) { Icon(Icons.Default.Share, "Share") }
                        DropdownMenu(shareMenu, { shareMenu = false }) {
                            DropdownMenuItem(text = { Text("Share as searchable PDF") }, onClick = {
                                shareMenu = false
                                vm.exportPdf(id) { Exporter.share(context, listOf(it), "application/pdf") }
                            })
                            DropdownMenuItem(text = { Text("Share as JPG images") }, onClick = {
                                shareMenu = false
                                vm.exportJpgs(id) { Exporter.share(context, it, "image/jpeg") }
                            })
                            DropdownMenuItem(text = { Text("Share as text") }, onClick = {
                                shareMenu = false
                                vm.exportText(id) { Exporter.share(context, listOf(it), "text/plain") }
                            })
                        }
                    }
                    Box {
                        IconButton(onClick = { menu = true }) { Icon(Icons.Default.MoreVert, "More") }
                        DropdownMenu(menu, { menu = false }) {
                            DropdownMenuItem(text = { Text("Extract text") }, onClick = {
                                menu = false
                                vm.ocr(id) { ocrText = it }
                            })
                            DropdownMenuItem(text = { Text("Save PDF to Google Drive") }, onClick = {
                                menu = false
                                vm.exportPdf(id) { Exporter.saveToDrive(context, it) }
                            })
                            DropdownMenuItem(text = { Text("Save PDF to phone") }, onClick = {
                                menu = false
                                savePdf.launch(Exporter.safeName(doc.name) + ".pdf")
                            })
                            DropdownMenuItem(text = { Text("Rename") }, onClick = { menu = false; rename = true })
                            DropdownMenuItem(text = { Text("Move to folder") }, onClick = { menu = false; move = true })
                            DropdownMenuItem(text = { Text("Delete", color = Red) }, onClick = { menu = false; delete = true })
                        }
                    }
                },
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(onClick = scan, icon = { Icon(Icons.Default.Add, null) }, text = { Text("Add pages") })
        },
    ) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(10.dp, 8.dp, 10.dp, 0.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { aiDialog = true }, modifier = Modifier.weight(1.4f)) {
                Icon(Icons.AutoMirrored.Filled.Send, null)
                Text(" Send to AI")
            }
            OutlinedButton(onClick = { vm.exportPdf(id) { Exporter.saveToDrive(context, it) } },
                modifier = Modifier.weight(1f)) { Text("Drive") }
            OutlinedButton(onClick = { vm.ocr(id) { ocrText = it } }, modifier = Modifier.weight(1f)) { Text("Text") }
        }
        LazyVerticalGrid(
            columns = GridCells.Fixed(3),
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(10.dp, 10.dp, 10.dp, 96.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            itemsIndexed(doc.pages, key = { _, p -> p.original }) { i, p ->
                Column(Modifier.clickable { onPage(i) }, horizontalAlignment = Alignment.CenterHorizontally) {
                    AsyncImage(
                        model = doc.fileOf(p),
                        contentDescription = "Page ${i + 1}",
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxWidth().aspectRatio(0.72f).background(Color.LightGray),
                    )
                    Text("${i + 1}")
                }
            }
        }
        }
    }

    if (aiDialog) {
        AiSendDialog(aiPrompt, allowPdf = true, onDismiss = { aiDialog = false }) { prompt, asPdf ->
            vm.sendToAi(id, null, null, asPdf, prompt) { files, mime -> Exporter.shareToAi(context, files, mime, prompt) }
        }
    }

    if (rename) {
        TextInputDialog("Rename", doc.name, "Save", { rename = false }) { vm.rename(id, it) }
    }
    if (move) {
        AlertDialog(
            onDismissRequest = { move = false },
            title = { Text("Move to folder") },
            text = {
                Column {
                    (listOf("") + folders).forEach { f ->
                        Row(Modifier.fillMaxWidth().clickable { vm.moveToFolder(id, f); move = false },
                            verticalAlignment = Alignment.CenterVertically) {
                            RadioButton(selected = doc.folder == f, onClick = { vm.moveToFolder(id, f); move = false })
                            Text(f.ifEmpty { "No folder" })
                        }
                    }
                    if (folders.isEmpty()) Text("Create folders from the home screen menu.", color = Color.Gray)
                }
            },
            confirmButton = { TextButton(onClick = { move = false }) { Text("Close") } },
        )
    }
    if (delete) {
        ConfirmDialog("Delete scan", "Delete \"${doc.name}\" and all its pages?", "Delete", { delete = false }) {
            vm.delete(id)
        }
    }
    ocrText?.let { text ->
        OcrDialog(text, onDismiss = { ocrText = null }) {
            Exporter.share(context, listOf(Exporter.text(context, doc.name, text)), "text/plain")
        }
    }
}
