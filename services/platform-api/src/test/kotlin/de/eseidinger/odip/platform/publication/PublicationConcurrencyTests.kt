package de.eseidinger.odip.platform.publication

import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.mock.web.MockHttpServletRequest
import java.util.UUID
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.test.assertEquals

@SpringBootTest
class PublicationConcurrencyTests(
    @Autowired private val service: PublicationService,
    @Autowired private val datasets: DatasetRepository,
    @Autowired private val contracts: PublicationContracts,
) {
    @Test fun `concurrent identical keys return exactly one draft`() {
        val dataset = datasets.saveAndFlush(DatasetEntity(name = "Concurrency ${UUID.randomUUID()}"))

        @Suppress("UNCHECKED_CAST")
        val fixture = contracts.mapper.readValue(javaClass.getResourceAsStream("/contract-fixtures/non-energy-mobility-counts-2024/manifest.json"), Map::class.java) as Map<String, Any?>
        val manifest = fixture + ("datasetId" to "concurrency-${UUID.randomUUID()}")
        val key = UUID.randomUUID().toString()
        val pool = Executors.newFixedThreadPool(2)
        try {
            val tasks = (1..2).map { Callable { service.create(MockHttpServletRequest(), DraftRequest(dataset.id, manifest), key)["id"] } }
            val results = pool.invokeAll(tasks).map { it.get(20, TimeUnit.SECONDS) }
            assertEquals(1, results.distinct().size)
        } finally {
            pool.shutdownNow()
        }
    }
}
