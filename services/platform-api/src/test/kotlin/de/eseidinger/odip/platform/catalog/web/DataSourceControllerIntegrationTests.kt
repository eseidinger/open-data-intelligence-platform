package de.eseidinger.odip.platform.catalog.web

import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.http.MediaType
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.header
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status

@SpringBootTest
@AutoConfigureMockMvc
class DataSourceControllerIntegrationTests(
    @Autowired private val mockMvc: MockMvc,
    @Autowired private val dataSourceRepository: DataSourceRepository,
) {
    @BeforeEach
    fun clearDataSources() {
        dataSourceRepository.deleteAll()
    }

    @Test
    fun `creates and lists a data source`() {
        mockMvc.perform(
            post("/api/data-sources")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {
                      "name": "ENTSO-E Transparency Platform",
                      "sourceType": "API",
                      "location": "https://transparency.entsoe.eu/api",
                      "owner": "ENTSO-E",
                      "license": "Open data terms",
                      "refreshCadence": "hourly"
                    }
                    """.trimIndent(),
                ),
        )
            .andExpect(status().isCreated)
            .andExpect(header().string("Location", org.hamcrest.Matchers.matchesPattern("/api/data-sources/.+")))
            .andExpect(jsonPath("$.name").value("ENTSO-E Transparency Platform"))
            .andExpect(jsonPath("$.sourceType").value("API"))

        mockMvc.perform(get("/api/data-sources"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$[0].name").value("ENTSO-E Transparency Platform"))
    }

    @Test
    fun `rejects duplicate source names`() {
        val request = """{"name":"Energy API","sourceType":"API","location":"https://example.test/api"}"""

        mockMvc.perform(post("/api/data-sources").contentType(MediaType.APPLICATION_JSON).content(request))
            .andExpect(status().isCreated)

        mockMvc.perform(post("/api/data-sources").contentType(MediaType.APPLICATION_JSON).content(request))
            .andExpect(status().isConflict)
    }
}
