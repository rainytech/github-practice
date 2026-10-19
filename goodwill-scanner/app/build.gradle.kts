plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.goodwill.scanner"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.goodwill.scanner"
        minSdk = 24
        targetSdk = 35
        versionCode = 4
        versionName = "2.2"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a") }
    }

    // Fixed key so every new build installs over the previous one.
    signingConfigs {
        create("goodwill") {
            storeFile = file("goodwill.keystore")
            storePassword = "goodwill"
            keyAlias = "goodwill"
            keyPassword = "goodwill"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("goodwill")
        }
        debug {
            signingConfig = signingConfigs.getByName("goodwill")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("com.google.android.gms:play-services-mlkit-document-scanner:16.0.0-beta1")
    implementation("com.google.mlkit:text-recognition:16.0.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.8.1")
}
