@file:OptIn(ExperimentalMaterial3Api::class)

package com.goodwill.scanner.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.goodwill.scanner.AppViewModel
import com.goodwill.scanner.ScanDoc
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun HomeScreen(vm: AppViewModel, onOpen: (String) -> Unit) {
    val docs by vm.docs.collectAsState()
    val folders by vm.folders.collectAsState()
    val bookMode by vm.bookMode.collectAsState()
    val autoClean by vm.autoClean.collectAsState()
    var selected by rememberSaveable { mutableStateOf<String?>(null) }
    var menu by remember { mutableStateOf(false) }
    var newFolder by remember { mutableStateOf(false) }
    var deleteFolder by remember { mutableStateOf(false) }
    val scan = rememberScanner { uris -> vm.importScan(null, uris, selected ?: "", onOpen) }
    val shown = docs.filter { selected == null || it.folder == selected }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Goodwill Scanner") },
                colors = barColors(),
                actions = {
                    Box {
                        IconButton(onClick = { menu = true }) { Icon(Icons.Default.MoreVert, "Menu") }
                        DropdownMenu(menu, { menu = false }) {
                            DropdownMenuItem(text = { Text("New folder") }, onClick = { menu = false; newFolder = true })
                            if (selected != null) {
                                DropdownMenuItem(text = { Text("Delete folder \"$selected\"") },
                                    onClick = { menu = false; deleteFolder = true })
                            }
                        }
                    }
                },
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(onClick = scan, icon = { Icon(Icons.Default.Add, null) }, text = { Text("Scan") })
        },
    ) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
            LazyRow(contentPadding = PaddingValues(12.dp, 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                item { FilterChip(selected == null, { selected = null }, { Text("All") }) }
                items(folders) { f -> FilterChip(selected == f, { selected = f }, { Text(f) }) }
            }
            SettingRow("Book mode", "Split a two-page spread into left and right pages",
                bookMode, vm::setBookMode)
            SettingRow("Clean text automatically", "White page, dark text, spine shadow removed",
                autoClean, vm::setAutoClean)
            HorizontalDivider()
            if (shown.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No scans yet.\nTap Scan to start.", textAlign = TextAlign.Center, color = Color.Gray)
                }
            } else {
                LazyColumn(contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 96.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(shown, key = { it.id }) { d -> DocRow(d) { onOpen(d.id) } }
                }
            }
        }
    }

    if (newFolder) {
        TextInputDialog("New folder", "", "Create", { newFolder = false }) {
            vm.addFolder(it)
            selected = it
        }
    }
    if (deleteFolder) {
        val name = selected ?: ""
        ConfirmDialog("Delete folder", "Delete folder \"$name\"? Its scans are kept and moved to All.", "Delete",
            { deleteFolder = false }) {
            vm.deleteFolder(name)
            selected = null
        }
    }
}

private val dateFormat = SimpleDateFormat("d MMM yyyy, HH:mm", Locale.ENGLISH)

@Composable
private fun DocRow(d: ScanDoc, onClick: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(56.dp, 76.dp).background(Color.LightGray)) {
                d.pages.firstOrNull()?.let {
                    AsyncImage(model = d.fileOf(it), contentDescription = null,
                        contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
                }
            }
            Spacer(Modifier.width(12.dp))
            Column {
                Text(d.name, fontWeight = FontWeight.Bold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                val pages = if (d.pages.size == 1) "1 page" else "${d.pages.size} pages"
                Text("$pages · ${dateFormat.format(Date(d.created))}", style = MaterialTheme.typography.bodySmall)
                if (d.folder.isNotEmpty()) {
                    Text(d.folder, style = MaterialTheme.typography.bodySmall, color = Purple)
                }
            }
        }
    }
}
