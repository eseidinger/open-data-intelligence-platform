package de.eseidinger.odip.platform.ingestion.service

import java.util.UUID

data class TransformationRequest(val id: String, val data: Map<String, Any?>)
interface ArtifactTransformation {
    val id: String
    fun apply(rawArtifactId: UUID, data: Map<String, Any?>)
}
