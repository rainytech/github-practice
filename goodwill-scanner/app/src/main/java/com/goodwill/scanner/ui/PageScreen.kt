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
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.goodwill.scanner.AppViewModel
import com.goodwill.scanner.PageFilter
import kotlinx.coroutines.launch

@Composable
fun PageScreen(vm: AppViewModel, id: String, start: Int, onBack: () -> Unit) {
    val docs by vm.docs.collectAsState()
    val doc = docs.find { it.id == id }
    if (doc == null || doc.pages.isEmpty()) {
        LaunchedEffect(Unit) { onBack() }
        return
    }
    val pager = rememberPagerState(initialPage = start.coerceIn(0, doc.pages.lastIndex)) { doc.pages.size }
    val index = pager.currentPage.coerceIn(0, doc.pages.lastIndex)
    val page = doc.pages[index]
    val scope = rememberCoroutineScope()
    var confirmDelete by remember { mutableStateOf(false) }

    fun moveTo(target: Int) = vm.movePage(id, index, target) { scope.launch { pager.scrollToPage(target) } }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Page ${index + 1} of ${doc.pages.size}") },
                colors = barColors(),
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") }
                },
                actions = {
                    IconButton(onClick = { confirmDelete = true }) { Icon(Icons.Default.Delete, "Delete page") }
                },
            )
        },
        bottomBar = {
            Surface(tonalElevation = 3.dp) {
                Column(Modifier.navigationBarsPadding().padding(8.dp)) {
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        PageFilter.entries.forEach { f ->
                            FilterChip(page.filter == f, { if (page.filter != f) vm.editPage(id, index, f, page.rotation) },
                                { Text(f.label) })
                        }
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                        TextButton(enabled = index > 0, onClick = { moveTo(index - 1) }) {
                            Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, null)
                            Text("Move")
                        }
                        TextButton(onClick = { vm.editPage(id, index, page.filter, page.rotation + 90) }) {
                            Icon(Icons.Default.Refresh, null)
                            Text(" Rotate")
                        }
                        TextButton(enabled = index < doc.pages.lastIndex, onClick = { moveTo(index + 1) }) {
                            Text("Move")
                            Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null)
                        }
                    }
                }
            }
        },
    ) { pad ->
        HorizontalPager(
            state = pager,
            modifier = Modifier.padding(pad).fillMaxSize().background(Color(0xFF303030)),
            key = { doc.pages[it].original },
        ) { i ->
            AsyncImage(
                model = doc.fileOf(doc.pages[i]),
                contentDescription = "Page ${i + 1}",
                contentScale = ContentScale.Fit,
                modifier = Modifier.fillMaxSize().padding(8.dp),
            )
        }
    }

    if (confirmDelete) {
        ConfirmDialog("Delete page", "Delete page ${index + 1}?", "Delete", { confirmDelete = false }) {
            vm.deletePage(id, index)
        }
    }
}
