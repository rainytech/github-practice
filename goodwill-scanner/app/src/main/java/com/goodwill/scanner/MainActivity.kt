package com.goodwill.scanner

import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.viewmodel.compose.viewModel
import com.goodwill.scanner.ui.BusyDialog
import com.goodwill.scanner.ui.DocumentScreen
import com.goodwill.scanner.ui.GoodwillTheme
import com.goodwill.scanner.ui.HomeScreen
import com.goodwill.scanner.ui.PageScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT))
        setContent { GoodwillTheme { App() } }
    }
}

private sealed interface Screen {
    data object Home : Screen
    data class Doc(val id: String) : Screen
    data class Pages(val id: String, val index: Int) : Screen
}

@Composable
private fun App(vm: AppViewModel = viewModel()) {
    var screen by remember { mutableStateOf<Screen>(Screen.Home) }
    val busy by vm.busy.collectAsState()

    BackHandler(enabled = screen != Screen.Home) {
        screen = when (val s = screen) {
            is Screen.Pages -> Screen.Doc(s.id)
            else -> Screen.Home
        }
    }

    when (val s = screen) {
        Screen.Home -> HomeScreen(vm, onOpen = { screen = Screen.Doc(it) })
        is Screen.Doc -> DocumentScreen(vm, s.id,
            onBack = { screen = Screen.Home },
            onPage = { screen = Screen.Pages(s.id, it) })
        is Screen.Pages -> PageScreen(vm, s.id, s.index, onBack = { screen = Screen.Doc(s.id) })
    }

    busy?.let { BusyDialog(it) }
}
