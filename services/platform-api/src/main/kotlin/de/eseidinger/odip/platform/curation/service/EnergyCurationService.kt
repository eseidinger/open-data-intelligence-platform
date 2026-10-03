package de.eseidinger.odip.platform.curation.service

import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import de.eseidinger.odip.platform.catalog.persistence.DatasetVersionRepository
import de.eseidinger.odip.platform.catalog.domain.DatasetVersionEntity
import de.eseidinger.odip.platform.curation.domain.EnergyObservationEntity
import de.eseidinger.odip.platform.curation.persistence.EnergyObservationRepository
import de.eseidinger.odip.platform.curation.web.CreateEnergyObservationRequest
import de.eseidinger.odip.platform.ingestion.persistence.RawArtifactRepository
import de.eseidinger.odip.platform.ingestion.persistence.RawArtifactValidationRepository
import java.util.UUID
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.server.ResponseStatusException

@Service
class EnergyCurationService(
    private val datasets: DatasetRepository,
    private val datasetVersions: DatasetVersionRepository,
    private val artifacts: RawArtifactRepository,
    private val artifactValidations: RawArtifactValidationRepository,
    private val observations: EnergyObservationRepository,
) {
    @Transactional
    fun curate(rawArtifactId: UUID, request: CreateEnergyObservationRequest): EnergyObservationEntity {
        val artifact = artifacts.findById(rawArtifactId).orElseThrow { notFound("Raw artifact", rawArtifactId) }
        val sourceId = requireNotNull(artifact.source).id
        val dataset = datasets.findAllBySources_Id(sourceId).singleOrNull()
            ?: throw ResponseStatusException(HttpStatus.CONFLICT, "Raw artifact $rawArtifactId must map to exactly one dataset")
        val version = publishVersion(dataset.id, artifact.id)
        return observations.findByRawArtifact_IdAndIndicatorCodeAndGeoCodeAndObservationYearAndUnitCode(rawArtifactId, request.indicatorCode, request.geoCode, request.observationYear, request.unitCode)
            ?: observations.save(EnergyObservationEntity(rawArtifact = artifact, dataset = dataset, datasetVersion = version, indicatorCode = request.indicatorCode, geoCode = request.geoCode, observationYear = request.observationYear, unitCode = request.unitCode, observationValue = request.observationValue))
    }

    @Transactional(readOnly = true)
    fun list(datasetId: UUID): List<EnergyObservationEntity> {
        if (!datasets.existsById(datasetId)) throw notFound("Dataset", datasetId)
        return observations.findAllByDataset_IdOrderByObservationYearDesc(datasetId)
    }

    private fun notFound(type: String, id: UUID) = ResponseStatusException(HttpStatus.NOT_FOUND, "$type $id was not found")

    private fun publishVersion(datasetId: UUID, artifactId: UUID) = datasetVersions.findByDataset_IdAndRawArtifact_Id(datasetId, artifactId)
        ?: datasetVersions.save(
            DatasetVersionEntity(
                dataset = datasets.getReferenceById(datasetId),
                rawArtifact = artifacts.getReferenceById(artifactId),
                versionNumber = (datasetVersions.findFirstByDataset_IdOrderByVersionNumberDesc(datasetId)?.versionNumber ?: 0) + 1,
                schemaDefinition = mapOf("name" to "energy_observation", "fields" to listOf("indicatorCode", "geoCode", "observationYear", "unitCode", "observationValue")),
                qualitySummary = artifactValidations.findByRawArtifact_Id(artifactId)?.let { validation -> mapOf("validationStatus" to validation.status.name, "detectedFormat" to validation.detectedFormat, "recordCount" to validation.recordCount, "schemaFingerprint" to validation.schemaFingerprint) } ?: mapOf("validationStatus" to "NOT_RECORDED"),
            ),
        )
}
