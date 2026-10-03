package de.eseidinger.odip.platform.curation.web

import de.eseidinger.odip.platform.curation.domain.EnergyObservationEntity
import de.eseidinger.odip.platform.curation.service.EnergyCurationService
import jakarta.validation.Valid
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Max
import jakarta.validation.constraints.Min
import jakarta.validation.constraints.Pattern
import jakarta.validation.constraints.PositiveOrZero
import java.math.BigDecimal
import java.time.Instant
import java.util.UUID
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api")
class EnergyCurationController(private val curation: EnergyCurationService) {
    @PostMapping("/raw-artifacts/{artifactId}/energy-observations")
    fun curate(@PathVariable artifactId: UUID, @Valid @RequestBody request: CreateEnergyObservationRequest): ResponseEntity<EnergyObservationResponse> = ResponseEntity.status(HttpStatus.CREATED).body(curation.curate(artifactId, request).toResponse())

    @GetMapping("/datasets/{datasetId}/energy-observations")
    fun list(@PathVariable datasetId: UUID): List<EnergyObservationResponse> = curation.list(datasetId).map { it.toResponse() }
}

data class CreateEnergyObservationRequest(
    @field:NotBlank @field:Pattern(regexp = "^[A-Z0-9_]+$") val indicatorCode: String,
    @field:NotBlank @field:Pattern(regexp = "^[A-Z]{2,32}$") val geoCode: String,
    @field:Min(1900) @field:Max(2200) val observationYear: Int,
    @field:NotBlank @field:Pattern(regexp = "^[A-Z0-9_]+$") val unitCode: String,
    val observationValue: BigDecimal,
)

data class EnergyObservationResponse(val id: UUID, val datasetId: UUID, val datasetVersionId: UUID?, val datasetVersionNumber: Long?, val rawArtifactId: UUID, val indicatorCode: String, val geoCode: String, val observationYear: Int, val unitCode: String, val observationValue: BigDecimal, val createdAt: Instant)
private fun EnergyObservationEntity.toResponse() = EnergyObservationResponse(id, requireNotNull(dataset).id, datasetVersion?.id, datasetVersion?.versionNumber, requireNotNull(rawArtifact).id, indicatorCode, geoCode, observationYear, unitCode, observationValue, createdAt)
