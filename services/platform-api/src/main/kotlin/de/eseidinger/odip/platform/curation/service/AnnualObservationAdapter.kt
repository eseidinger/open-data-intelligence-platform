package de.eseidinger.odip.platform.curation.service

import de.eseidinger.odip.platform.curation.web.CreateEnergyObservationRequest
import de.eseidinger.odip.platform.ingestion.service.ArtifactTransformation
import org.springframework.stereotype.Component
import java.math.BigDecimal
import java.util.UUID

@Component
class AnnualObservationAdapter(private val curation: EnergyCurationService) : ArtifactTransformation {
    override val id = "eurostat-renewable-share/v1"
    override fun apply(rawArtifactId: UUID, data: Map<String, Any?>) {
        curation.curate(rawArtifactId, CreateEnergyObservationRequest(
            data.getValue("indicatorCode").toString(), data.getValue("geoCode").toString(),
            data.getValue("observationYear").toString().toInt(), data.getValue("unitCode").toString(),
            BigDecimal(data.getValue("observationValue").toString())))
    }
}
