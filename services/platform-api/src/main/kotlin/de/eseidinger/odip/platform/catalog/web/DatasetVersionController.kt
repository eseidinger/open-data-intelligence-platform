package de.eseidinger.odip.platform.catalog.web

import de.eseidinger.odip.platform.catalog.domain.DatasetVersionEntity
import de.eseidinger.odip.platform.catalog.service.DatasetVersionService
import java.time.Instant
import java.util.UUID
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/datasets")
class DatasetVersionController(private val versions: DatasetVersionService) {
    @GetMapping("/{datasetId}/versions")
    fun list(@PathVariable datasetId: UUID): List<DatasetVersionResponse> = versions.list(datasetId).map { it.toResponse() }
}

data class DatasetVersionResponse(val id: UUID, val versionNumber: Long, val status: String, val rawArtifactId: UUID?, val schemaDefinition: Map<String, Any?>, val qualitySummary: Map<String, Any?>, val createdAt: Instant)
private fun DatasetVersionEntity.toResponse() = DatasetVersionResponse(id, versionNumber, status, rawArtifact?.id, schemaDefinition, qualitySummary, createdAt)
