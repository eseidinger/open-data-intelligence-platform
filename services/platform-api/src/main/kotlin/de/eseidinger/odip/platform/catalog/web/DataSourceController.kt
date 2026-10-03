package de.eseidinger.odip.platform.catalog.web

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import de.eseidinger.odip.platform.catalog.domain.DataSourceType
import de.eseidinger.odip.platform.catalog.service.DataSourceService
import jakarta.validation.Valid
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Pattern
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
@RequestMapping("/api/data-sources")
class DataSourceController(
    private val dataSourceService: DataSourceService,
) {
    @GetMapping
    fun list(): List<DataSourceResponse> = dataSourceService.list().map(::toResponse)

    @PostMapping
    fun create(@Valid @RequestBody request: CreateDataSourceRequest): ResponseEntity<DataSourceResponse> {
        val source = dataSourceService.create(request)
        return ResponseEntity
            .created(URI.create("/api/data-sources/${source.id}"))
            .body(toResponse(source))
    }

    private fun toResponse(source: DataSourceEntity) = DataSourceResponse(
        id = source.id,
        name = source.name,
        sourceType = source.sourceType,
        location = source.location,
        owner = source.owner,
        license = source.license,
        refreshCadence = source.refreshCadence,
        createdAt = source.createdAt,
        updatedAt = source.updatedAt,
    )
}

data class CreateDataSourceRequest(
    @field:NotBlank
    @field:Size(max = 255)
    val name: String,
    val sourceType: DataSourceType,
    @field:NotBlank
    @field:Size(max = 2048)
    @field:Pattern(regexp = "^[a-zA-Z][a-zA-Z0-9+.-]*:.+")
    val location: String,
    @field:Size(max = 255)
    val owner: String? = null,
    @field:Size(max = 2048)
    val license: String? = null,
    @field:Size(max = 255)
    val refreshCadence: String? = null,
)

data class DataSourceResponse(
    val id: UUID,
    val name: String,
    val sourceType: DataSourceType,
    val location: String,
    val owner: String?,
    val license: String?,
    val refreshCadence: String?,
    val createdAt: Instant,
    val updatedAt: Instant,
)
