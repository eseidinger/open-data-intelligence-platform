package de.eseidinger.odip.platform.ingestion.web

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import de.eseidinger.odip.platform.catalog.domain.DataSourceType
import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
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
class IngestionControllerIntegrationTests(@Autowired private val mockMvc: MockMvc, @Autowired private val sources: DataSourceRepository) {
    @Test
    fun `queues and completes a raw ingestion run`() {
        val source = sources.save(DataSourceEntity(name = "Fixture ${java.util.UUID.randomUUID()}", sourceType = DataSourceType.API, location = "https://example.test/data.json"))
        val queued = mockMvc.perform(post("/api/data-sources/${source.id}/ingestions"))
            .andExpect(status().isAccepted).andExpect(jsonPath("$.status").value("QUEUED")).andReturn()
        val runId = com.jayway.jsonpath.JsonPath.read<String>(queued.response.contentAsString, "$.id")

        mockMvc.perform(get("/api/pipeline-runs/$runId/job")).andExpect(status().isOk).andExpect(jsonPath("$.location").value(source.location))
        mockMvc.perform(post("/api/pipeline-runs/$runId/started")).andExpect(status().isOk).andExpect(jsonPath("$.status").value("RUNNING"))
        mockMvc.perform(post("/api/pipeline-runs/$runId/completed").contentType(MediaType.APPLICATION_JSON).content("""{"storageUri":"s3://odip-raw/raw/test","contentType":"application/json","contentLength":2,"checksumSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","sourceVersion":"fixture-v1"}"""))
            .andExpect(status().isOk).andExpect(jsonPath("$.status").value("SUCCEEDED"))
        mockMvc.perform(get("/api/pipeline-runs/$runId/artifacts"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$[0].storageUri").value("s3://odip-raw/raw/test"))
            .andExpect(jsonPath("$[0].contentType").value("application/json"))
            .andExpect(jsonPath("$[0].contentLength").value(2))
            .andExpect(jsonPath("$[0].checksumSha256").value("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))
            .andExpect(jsonPath("$[0].sourceVersion").value("fixture-v1"))
    }
}
