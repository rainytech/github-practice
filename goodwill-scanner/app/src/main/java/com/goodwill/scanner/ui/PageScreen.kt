@file:OptIn(ExperimentalMaterial3Api::class)

package com.goodwill.scanner.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.goodwill.scanner.AppViewModel
import com.goodwill.scanner.CropBox
import com.goodwill.scanner.Exporter
import com.goodwill.scanner.PageFilter
import kotlinx.coroutines.launch

private val FULL_BOX = CropBox(0.05f, 0.05f, 0.95f, 0.95f)

@Composable
fun PageScreen(vm: AppViewModel, id: String, start: Int, onBack: () -> Unit) {
    val docs by vm.docs.collectAsState()
    val aiPrompt by vm.aiPrompt.collectAsState()
    val doc = docs.find { it.id == id }
    if (doc == null || doc.pages.isEmpty()) {
        LaunchedEffect(Unit) { onBack() }
        return
    }
    val context = LocalContext.current
    val pager = rememberPagerState(initialPage = start.coerceIn(0, doc.pages.lastIndex)) { doc.pages.size }
    val index = pager.currentPage.coerceIn(0, doc.pages.lastIndex)
    val page = doc.pages[index]
    val scope = rememberCoroutineScope()
    var confirmDelete by remember { mutableStateOf(false) }
    var cropping by remember { mutableStateOf(false) }
    var cropBox by remember { mutableStateOf(FULL_BOX) }
    // null = no dialog; otherwise the crop to send (FULL page when not cropping).
    var aiSend by remember { mutableStateOf<CropBox?>(null) }
    var aiDialog by remember { mutableStateOf(false) }

    fun moveTo(target: Int) = vm.movePage(id, index, target) { scope.launch { pager.scrollToPage(target) } }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (cropping) "Crop page ${index + 1}" else "Page ${index + 1} of ${doc.pages.size}") },
                colors = barColors(),
                navigationIcon = {
                    IconButton(onClick = { if (cropping) cropping = false else onBack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                    }
                },
                actions = {
                    if (!cropping) {
                        IconButton(onClick = { aiSend = null; aiDialog = true }) {
                            Icon(Icons.AutoMirrored.Filled.Send, "Send page to AI")
                        }
                        IconButton(onClick = { confirmDelete = true }) { Icon(Icons.Default.Delete, "Delete page") }
                    }
                },
            )
        },
        bottomBar = {
            Surface(tonalElevation = 3.dp) {
                Column(Modifier.navigationBarsPadding().padding(8.dp)) {
                    if (cropping) {
                        Text("Drag the corners around one question.", Modifier.padding(4.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { cropping = false }, Modifier.weight(1f)) { Text("Cancel") }
                            OutlinedButton(onClick = {
                                vm.cropPage(id, index, cropBox)
                                cropping = false
                            }, Modifier.weight(1f)) { Text("Save crop") }
                            Button(onClick = { aiSend = cropBox; aiDialog = true }, Modifier.weight(1.2f)) {
                                Text("Send to AI")
                            }
                        }
                    } else {
                        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            PageFilter.entries.forEach { f ->
                                FilterChip(page.filter == f,
                                    { if (page.filter != f) vm.editPage(id, index, f, page.rotation, page.crop) },
                                    { Text(f.label) })
                            }
                        }
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                            IconButton(enabled = index > 0, onClick = { moveTo(index - 1) }) {
                                Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, "Move page left")
                            }
                            TextButton(onClick = { cropBox = FULL_BOX; cropping = true }) {
                                Icon(Icons.Default.Edit, null)
                                Text(" Crop")
                            }
                            if (page.crop != null) {
                                TextButton(onClick = { vm.editPage(id, index, page.filter, page.rotation, null) }) {
                                    Text("Undo crop")
                                }
                            }
                            // Rotating clears the crop, which was drawn for the old orientation.
                            TextButton(onClick = { vm.editPage(id, index, page.filter, page.rotation + 90, null) }) {
                                Icon(Icons.Default.Refresh, null)
                                Text(" Rotate")
                            }
                            IconButton(enabled = index < doc.pages.lastIndex, onClick = { moveTo(index + 1) }) {
                                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, "Move page right")
                            }
                        }
                    }
                }
            }
        },
    ) { pad ->
        val area = Modifier.padding(pad).fillMaxSize().background(Color(0xFF303030))
        if (cropping) {
            CropEditor(doc.fileOf(page), cropBox, { cropBox = it }, area.padding(16.dp))
        } else {
            HorizontalPager(state = pager, modifier = area, key = { doc.pages[it].original }) { i ->
                AsyncImage(
                    model = doc.fileOf(doc.pages[i]),
                    contentDescription = "Page ${i + 1}",
                    contentScale = ContentScale.Fit,
                    modifier = Modifier.fillMaxSize().padding(8.dp),
                )
            }
        }
    }

    if (aiDialog) {
        val crop = aiSend
        AiSendDialog(aiPrompt, allowPdf = false, onDismiss = { aiDialog = false }) { prompt, _ ->
            vm.sendToAi(id, index, crop, false, prompt) { files, mime ->
                Exporter.shareToAi(context, files, mime, prompt)
            }
            cropping = false
        }
    }
    if (confirmDelete) {
        ConfirmDialog("Delete page", "Delete page ${index + 1}?", "Delete", { confirmDelete = false }) {
            vm.deletePage(id, index)
        }
    }
}
