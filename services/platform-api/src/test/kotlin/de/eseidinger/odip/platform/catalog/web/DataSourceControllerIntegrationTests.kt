package de.eseidinger.odip.platform.catalog.web

import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.http.MediaType
import org.springframework.transaction.annotation.Transactional
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.header
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class DataSourceControllerIntegrationTests(
    @Autowired private val mockMvc: MockMvc,
) {
    @Test
    fun `creates and lists a data source`() {
        val sourceName = "ENTSO-E Transparency Platform ${java.util.UUID.randomUUID()}"
        mockMvc.perform(
            post("/api/data-sources")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {
                      "name": "$sourceName",
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
            .andExpect(jsonPath("$.name").value(sourceName))
            .andExpect(jsonPath("$.sourceType").value("API"))

        mockMvc.perform(get("/api/data-sources"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$[?(@.name == '%s')]", sourceName).isNotEmpty())
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
