package de.eseidinger.odip.platform.ingestion.web

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import de.eseidinger.odip.platform.catalog.domain.DataSourceType
import de.eseidinger.odip.platform.catalog.domain.DatasetClassification
import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.http.MediaType
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import org.springframework.transaction.annotation.Transactional

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class IngestionControllerIntegrationTests(@Autowired private val mockMvc: MockMvc, @Autowired private val sources: DataSourceRepository, @Autowired private val datasets: DatasetRepository) {
    @Test
    fun `atomically claims the next queued run`() {
        val source = sources.save(DataSourceEntity(name = "Claim fixture ${java.util.UUID.randomUUID()}", sourceType = DataSourceType.API, location = "https://example.test/claim.json", refreshCadence = "annual"))
        mockMvc.perform(post("/api/data-sources/${source.id}/ingestions")).andExpect(status().isAccepted)

        mockMvc.perform(post("/api/pipeline-runs/claim-next"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.location").value(source.location))
        mockMvc.perform(post("/api/pipeline-runs/claim-next")).andExpect(status().isNoContent)
    }

    @Test
    fun `queues and completes a raw ingestion run`() {
        val source = sources.save(DataSourceEntity(name = "Fixture ${java.util.UUID.randomUUID()}", sourceType = DataSourceType.API, location = "https://example.test/data.json", refreshCadence = "annual"))
        val dataset = datasets.save(DatasetEntity(name = "Fixture dataset ${java.util.UUID.randomUUID()}", classification = DatasetClassification.PUBLIC, sources = mutableSetOf(source)))
        val queued = mockMvc.perform(post("/api/data-sources/${source.id}/ingestions"))
            .andExpect(status().isAccepted).andExpect(jsonPath("$.status").value("QUEUED")).andReturn()
        val runId = com.jayway.jsonpath.JsonPath.read<String>(queued.response.contentAsString, "$.id")

        mockMvc.perform(get("/api/pipeline-runs/$runId/job")).andExpect(status().isOk).andExpect(jsonPath("$.location").value(source.location))
        mockMvc.perform(post("/api/pipeline-runs/$runId/started")).andExpect(status().isOk).andExpect(jsonPath("$.status").value("RUNNING"))
        mockMvc.perform(post("/api/pipeline-runs/$runId/completed").contentType(MediaType.APPLICATION_JSON).content("""{"payload":"e30=","contentType":"application/json","contentLength":2,"checksumSha256":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","sourceVersion":"fixture-v1","validation":{"status":"VALID","detectedFormat":"JSON","recordCount":1,"schemaFingerprint":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},"energyObservation":{"indicatorCode":"RENEWABLE_ENERGY_SHARE","geoCode":"DE","observationYear":2024,"unitCode":"PC","observationValue":22.474}}"""))
            .andExpect(status().isOk).andExpect(jsonPath("$.status").value("SUCCEEDED"))
        mockMvc.perform(get("/api/pipeline-runs/$runId/artifacts"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$[0].storageUri").value(org.hamcrest.Matchers.startsWith("postgres://raw-artifacts/")))
            .andExpect(jsonPath("$[0].contentType").value("application/json"))
            .andExpect(jsonPath("$[0].contentLength").value(2))
            .andExpect(jsonPath("$[0].checksumSha256").value("44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"))
            .andExpect(jsonPath("$[0].sourceVersion").value("fixture-v1"))
            .andExpect(jsonPath("$[0].validation.status").value("VALID"))
            .andExpect(jsonPath("$[0].validation.detectedFormat").value("JSON"))
            .andExpect(jsonPath("$[0].validation.recordCount").value(1))
            .andExpect(jsonPath("$[0].validation.schemaFingerprint").value("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))
        val artifacts = mockMvc.perform(get("/api/pipeline-runs/$runId/artifacts")).andReturn()
        val artifactId = com.jayway.jsonpath.JsonPath.read<String>(artifacts.response.contentAsString, "$[0].id")
        mockMvc.perform(get("/api/raw-artifacts/$artifactId/content"))
            .andExpect(status().isOk)
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.content().contentType(MediaType.APPLICATION_JSON))
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.content().bytes("{}".toByteArray()))
        mockMvc.perform(get("/api/datasets/${dataset.id}/energy-observations"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$[0].indicatorCode").value("RENEWABLE_ENERGY_SHARE"))
            .andExpect(jsonPath("$[0].geoCode").value("DE"))
            .andExpect(jsonPath("$[0].observationYear").value(2024))
            .andExpect(jsonPath("$[0].unitCode").value("PC"))
            .andExpect(jsonPath("$[0].observationValue").value(22.474))
            .andExpect(jsonPath("$[0].datasetVersionNumber").value(1))
            .andExpect(jsonPath("$[0].datasetVersionId").isNotEmpty())
        mockMvc.perform(get("/api/datasets/${dataset.id}/versions"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$[0].versionNumber").value(1))
            .andExpect(jsonPath("$[0].status").value("PUBLISHED"))
            .andExpect(jsonPath("$[0].rawArtifactId").isNotEmpty())
            .andExpect(jsonPath("$[0].qualitySummary.validationStatus").value("VALID"))
        mockMvc.perform(get("/api/datasets/${dataset.id}/summary"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.latestVersionNumber").value(1))
            .andExpect(jsonPath("$.freshnessStatus").value("FRESH"))
            .andExpect(jsonPath("$.validationStatus").value("VALID"))
            .andExpect(jsonPath("$.recordCount").value(1))
    }
}
