package de.eseidinger.odip.platform.catalog.web

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import de.eseidinger.odip.platform.catalog.domain.DataSourceType
import de.eseidinger.odip.platform.catalog.domain.DatasetClassification
import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import de.eseidinger.odip.platform.catalog.service.DatasetService
import jakarta.validation.Valid
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.NotEmpty
import jakarta.validation.constraints.Size
import java.net.URI
import java.time.Instant
import java.util.UUID
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/datasets")
class DatasetController(
    private val datasetService: DatasetService,
) {
    @GetMapping
    fun list(): List<DatasetResponse> = datasetService.list().map(::toResponse)

    @PostMapping
    fun create(@Valid @RequestBody request: CreateDatasetRequest): ResponseEntity<DatasetResponse> {
        val dataset = datasetService.create(request)
        return ResponseEntity
            .created(URI.create("/api/datasets/${dataset.id}"))
            .body(toResponse(dataset))
    }

    private fun toResponse(dataset: DatasetEntity) = DatasetResponse(
        id = dataset.id,
        name = dataset.name,
        description = dataset.description,
        owner = dataset.owner,
        classification = dataset.classification,
        sources = dataset.sources.sortedBy { it.name }.map(::toSourceSummary),
        createdAt = dataset.createdAt,
        updatedAt = dataset.updatedAt,
    )

    private fun toSourceSummary(source: DataSourceEntity) = SourceSummary(
        id = source.id,
        name = source.name,
        sourceType = source.sourceType,
    )
}

data class CreateDatasetRequest(
    @field:NotBlank
    @field:Size(max = 255)
    val name: String,
    @field:Size(max = 10_000)
    val description: String? = null,
    @field:Size(max = 255)
    val owner: String? = null,
    val classification: DatasetClassification,
    @field:NotEmpty
    val sourceIds: List<UUID>,
)

data class DatasetResponse(
    val id: UUID,
    val name: String,
    val description: String?,
    val owner: String?,
    val classification: DatasetClassification,
    val sources: List<SourceSummary>,
    val createdAt: Instant,
    val updatedAt: Instant,
)

data class SourceSummary(
    val id: UUID,
    val name: String,
    val sourceType: DataSourceType,
)
