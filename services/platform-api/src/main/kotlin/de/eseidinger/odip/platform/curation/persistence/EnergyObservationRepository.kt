package de.eseidinger.odip.platform.curation.persistence

import de.eseidinger.odip.platform.curation.domain.EnergyObservationEntity
import java.util.UUID
import org.springframework.data.jpa.repository.EntityGraph
import org.springframework.data.jpa.repository.JpaRepository

interface EnergyObservationRepository : JpaRepository<EnergyObservationEntity, UUID> {
    fun findByRawArtifact_IdAndIndicatorCodeAndGeoCodeAndObservationYearAndUnitCode(rawArtifactId: UUID, indicatorCode: String, geoCode: String, observationYear: Int, unitCode: String): EnergyObservationEntity?
    @EntityGraph(attributePaths = ["dataset", "datasetVersion", "rawArtifact"])
    fun findAllByDataset_IdOrderByObservationYearDesc(datasetId: UUID): List<EnergyObservationEntity>
}
