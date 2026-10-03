package de.eseidinger.odip.platform.curation.service

import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import de.eseidinger.odip.platform.curation.domain.EnergyObservationEntity
import de.eseidinger.odip.platform.curation.persistence.EnergyObservationRepository
import de.eseidinger.odip.platform.curation.web.CreateEnergyObservationRequest
import de.eseidinger.odip.platform.ingestion.persistence.RawArtifactRepository
import java.util.UUID
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.server.ResponseStatusException

@Service
class EnergyCurationService(
    private val datasets: DatasetRepository,
    private val artifacts: RawArtifactRepository,
    private val observations: EnergyObservationRepository,
) {
    @Transactional
    fun curate(rawArtifactId: UUID, request: CreateEnergyObservationRequest): EnergyObservationEntity {
        val artifact = artifacts.findById(rawArtifactId).orElseThrow { notFound("Raw artifact", rawArtifactId) }
        val sourceId = requireNotNull(artifact.source).id
        val dataset = datasets.findAllBySources_Id(sourceId).singleOrNull()
            ?: throw ResponseStatusException(HttpStatus.CONFLICT, "Raw artifact $rawArtifactId must map to exactly one dataset")
        return observations.findByRawArtifact_IdAndIndicatorCodeAndGeoCodeAndObservationYearAndUnitCode(rawArtifactId, request.indicatorCode, request.geoCode, request.observationYear, request.unitCode)
            ?: observations.save(EnergyObservationEntity(rawArtifact = artifact, dataset = dataset, indicatorCode = request.indicatorCode, geoCode = request.geoCode, observationYear = request.observationYear, unitCode = request.unitCode, observationValue = request.observationValue))
    }

    @Transactional(readOnly = true)
    fun list(datasetId: UUID): List<EnergyObservationEntity> {
        if (!datasets.existsById(datasetId)) throw notFound("Dataset", datasetId)
        return observations.findAllByDataset_IdOrderByObservationYearDesc(datasetId)
    }

    private fun notFound(type: String, id: UUID) = ResponseStatusException(HttpStatus.NOT_FOUND, "$type $id was not found")
}
