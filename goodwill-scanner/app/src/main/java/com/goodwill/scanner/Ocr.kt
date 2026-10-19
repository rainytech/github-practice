package com.goodwill.scanner

import android.graphics.BitmapFactory
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.tasks.await
import java.io.File

object Ocr {
    suspend fun recognize(files: List<File>): String {
        val client = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        try {
            return files.mapIndexed { i, f ->
                val bmp = BitmapFactory.decodeFile(f.path) ?: return@mapIndexed ""
                val text = client.process(InputImage.fromBitmap(bmp, 0)).await().text
                bmp.recycle()
                if (files.size > 1) "--- Page ${i + 1} ---\n$text" else text
            }.joinToString("\n\n").trim()
        } finally {
            client.close()
        }
    }
}
