package de.eseidinger.odip.platform.catalog.web

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import de.eseidinger.odip.platform.catalog.domain.DataSourceType
import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.http.MediaType
import org.springframework.transaction.annotation.Transactional
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class DatasetControllerIntegrationTests(
    @Autowired private val mockMvc: MockMvc,
    @Autowired private val dataSourceRepository: DataSourceRepository,
) {
    @Test
    fun `creates a dataset linked to a source`() {
        val source = dataSourceRepository.save(
            DataSourceEntity(
                name = "Energy API ${java.util.UUID.randomUUID()}",
                sourceType = DataSourceType.API,
                location = "https://example.test/energy",
            ),
        )

        mockMvc.perform(
            post("/api/datasets")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {
                      "name": "Energy prices ${java.util.UUID.randomUUID()}",
                      "description": "Historic day-ahead electricity prices",
                      "owner": "ODIP",
                      "classification": "PUBLIC",
                      "sourceIds": ["${source.id}"]
                    }
                    """.trimIndent(),
                ),
        )
            .andExpect(status().isCreated)
            .andExpect(jsonPath("$.classification").value("PUBLIC"))
            .andExpect(jsonPath("$.sources[0].id").value(source.id.toString()))
            .andExpect(jsonPath("$.sources[0].name").value(source.name))
    }

    @Test
    fun `rejects a dataset with an unknown source`() {
        mockMvc.perform(
            post("/api/datasets")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {
                      "name": "Unknown source ${java.util.UUID.randomUUID()}",
                      "classification": "PUBLIC",
                      "sourceIds": ["${java.util.UUID.randomUUID()}"]
                    }
                    """.trimIndent(),
                ),
        ).andExpect(status().isBadRequest)
    }
}
