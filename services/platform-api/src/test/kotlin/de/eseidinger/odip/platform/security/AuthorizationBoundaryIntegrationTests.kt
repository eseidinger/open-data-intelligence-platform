package de.eseidinger.odip.platform.security

import com.jayway.jsonpath.JsonPath
import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import de.eseidinger.odip.platform.catalog.domain.DataSourceType
import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import de.eseidinger.odip.platform.ingestion.domain.PipelineRunEntity
import de.eseidinger.odip.platform.ingestion.persistence.PipelineRunRepository
import de.eseidinger.odip.platform.publication.DatasetAccess
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.http.MediaType
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.content
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.header
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import org.springframework.transaction.annotation.Transactional
import java.util.UUID

/** These tests start after trusted platform admission; they do not simulate its role policy. */
@SpringBootTest(properties = ["odip.authorization.require-principal-context=true"])
@AutoConfigureMockMvc
@Transactional
class AuthorizationBoundaryIntegrationTests(
    @Autowired private val mvc: MockMvc,
    @Autowired private val datasets: DatasetRepository,
    @Autowired private val sources: DataSourceRepository,
    @Autowired private val runs: PipelineRunRepository,
    @Autowired private val access: DatasetAccess,
    @Autowired private val jdbc: JdbcTemplate,
) {
    private fun auth(builder: MockHttpServletRequestBuilder, principal: String = "operator", group: String = "grp_e2987e192a0a41b4a0273c71c14fef47") = builder
        .header("X-Platform-Principal-Id", principal)
        .header("X-Platform-Principal-Kind", "user")
        .header("X-Platform-Principal-Issuer", "https://identity.test")
        .header("X-Platform-Principal-Subject", principal)
        .header("X-Platform-Principal-Group-Ids", group)

    private fun fixture(): Pair<DataSourceEntity, DatasetEntity> {
        val source = sources.saveAndFlush(DataSourceEntity(name = "Source ${UUID.randomUUID()}", sourceType = DataSourceType.API, location = "https://github.com/fixture"))
        val dataset = datasets.saveAndFlush(DatasetEntity(name = "Dataset ${UUID.randomUUID()}", sources = mutableSetOf(source)))
        return source to dataset
    }

    private fun completion(token: String? = null) = """{"payload":"e30=","contentType":"application/json","contentLength":2,"checksumSha256":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"${token?.let { ",\"claimToken\":\"$it\"" } ?: ""}}"""

    @Test
    fun `operator group does not bypass catalog or ingestion read grants`() {
        val (source, dataset) = fixture()
        val run = runs.saveAndFlush(PipelineRunEntity(source = source))
        mvc.perform(auth(get("/api/datasets"))).andExpect(jsonPath("$.length()").value(0))
        mvc.perform(auth(get("/api/v1/operator-pipeline-runs"))).andExpect(jsonPath("$.length()").value(0))
        mvc.perform(auth(get("/api/v1/operator-pipeline-runs/${run.id}/artifacts"))).andExpect(status().isForbidden)
        access.grant(dataset.id, "operator", "READ")
        mvc.perform(auth(get("/api/datasets"))).andExpect(jsonPath("$[0].id").value(dataset.id.toString()))
        mvc.perform(auth(get("/api/v1/operator-pipeline-runs"))).andExpect(jsonPath("$[0].id").value(run.id.toString()))
        mvc.perform(auth(get("/api/v1/operator-pipeline-runs/${run.id}/artifacts"))).andExpect(status().isOk)
    }

    @Test
    fun `queue start and job retrieval require explicit ingestion permission`() {
        val (source, dataset) = fixture()
        val run = runs.saveAndFlush(PipelineRunEntity(source = source))
        access.grant(dataset.id, "operator", "READ")
        mvc.perform(auth(post("/api/data-sources/${source.id}/ingestions"))).andExpect(status().isForbidden)
        mvc.perform(auth(get("/api/pipeline-runs/${run.id}/job"))).andExpect(status().isForbidden)
        mvc.perform(auth(post("/api/pipeline-runs/${run.id}/started"))).andExpect(status().isForbidden)
        access.grant(dataset.id, "operator", "INGEST")
        mvc.perform(auth(get("/api/pipeline-runs/${run.id}/job"))).andExpect(status().isOk)
        mvc.perform(auth(post("/api/pipeline-runs/${run.id}/started"))).andExpect(status().isOk).andExpect(jsonPath("$.claimToken").isNotEmpty())
        mvc.perform(auth(post("/api/data-sources/${source.id}/ingestions"))).andExpect(status().isAccepted)
    }

    @Test
    fun `claim queue filters datasets even for operators`() {
        val (restrictedSource, _) = fixture()
        val restricted = runs.saveAndFlush(PipelineRunEntity(source = restrictedSource))
        mvc.perform(auth(post("/api/pipeline-runs/claim-next"))).andExpect(status().isNoContent)
        val (allowedSource, allowedDataset) = fixture()
        val allowed = runs.saveAndFlush(PipelineRunEntity(source = allowedSource))
        access.grant(allowedDataset.id, "operator", "INGEST")
        mvc.perform(auth(post("/api/pipeline-runs/claim-next"))).andExpect(status().isOk).andExpect(jsonPath("$.runId").value(allowed.id.toString()))
        mvc.perform(auth(post("/api/pipeline-runs/claim-next"))).andExpect(status().isNoContent)
        kotlin.test.assertEquals("QUEUED", runs.findById(restricted.id).orElseThrow().status.name)
    }

    @Test
    fun `completion always requires owner current claim and current ingestion grant`() {
        val (source, dataset) = fixture()
        val run = runs.saveAndFlush(PipelineRunEntity(source = source))
        access.grant(dataset.id, "operator", "INGEST")
        access.grant(dataset.id, "other", "INGEST")
        val started = mvc.perform(auth(post("/api/pipeline-runs/${run.id}/started"))).andExpect(status().isOk).andReturn()
        val token = JsonPath.read<String>(started.response.contentAsString, "$.claimToken")
        mvc.perform(auth(post("/api/pipeline-runs/${run.id}/completed").contentType(MediaType.APPLICATION_JSON).content(completion(token)), "other"))
            .andExpect(status().isForbidden)
        for (missingOrWrong in listOf(null, UUID.randomUUID().toString())) {
            mvc.perform(auth(post("/api/pipeline-runs/${run.id}/completed").contentType(MediaType.APPLICATION_JSON).content(completion(missingOrWrong))))
                .andExpect(status().isConflict).andExpect(jsonPath("$.code").value("stale_claim"))
        }
        repeat(2) {
            mvc.perform(auth(post("/api/pipeline-runs/${run.id}/completed").contentType(MediaType.APPLICATION_JSON).content(completion(token))))
                .andExpect(status().isOk).andExpect(jsonPath("$.status").value("SUCCEEDED"))
        }
        jdbc.update("DELETE FROM dataset_grant WHERE dataset_id=? AND principal_id='operator' AND permission='INGEST'", dataset.id)
        mvc.perform(auth(post("/api/pipeline-runs/${run.id}/completed").contentType(MediaType.APPLICATION_JSON).content(completion(token))))
            .andExpect(status().isForbidden)
    }

    @Test
    fun `operators cannot fail unowned queued or running work`() {
        val (source, dataset) = fixture()
        val run = runs.saveAndFlush(PipelineRunEntity(source = source))
        access.grant(dataset.id, "operator", "INGEST")
        access.grant(dataset.id, "other", "INGEST")
        fun fail(principal: String) = mvc.perform(auth(post("/api/pipeline-runs/${run.id}/failed").contentType(MediaType.APPLICATION_JSON).content("""{"reason":"test failure"}"""), principal))
        fail("operator").andExpect(status().isForbidden)
        mvc.perform(auth(post("/api/pipeline-runs/${run.id}/started"), "other")).andExpect(status().isOk)
        fail("operator").andExpect(status().isForbidden)
        fail("other").andExpect(status().isOk).andExpect(jsonPath("$.status").value("FAILED"))
    }

    @Test
    fun `input capture uses its generated claim and does not grant raw read access`() {
        val (source, dataset) = fixture()
        val body = """{"sourceId":"${source.id}","input":${completion()}}"""
        mvc.perform(auth(post("/api/v1/reference-inputs").contentType(MediaType.APPLICATION_JSON).content(body))).andExpect(status().isForbidden)
        access.grant(dataset.id, "operator", "INGEST")
        val captured = mvc.perform(auth(post("/api/v1/reference-inputs").contentType(MediaType.APPLICATION_JSON).content(body)))
            .andExpect(status().isOk).andReturn()
        val artifact = JsonPath.read<String>(captured.response.contentAsString, "$.rawArtifactId")
        mvc.perform(auth(get("/api/raw-artifacts/$artifact/content"))).andExpect(status().isForbidden)
        access.grant(dataset.id, "operator", "READ")
        mvc.perform(auth(get("/api/raw-artifacts/$artifact/content"))).andExpect(status().isOk).andExpect(content().bytes("{}".toByteArray()))
    }

    @Test
    fun `unlinked sources require dataset registration before ingestion`() {
        val source = sources.saveAndFlush(DataSourceEntity(name = "Unlinked ${UUID.randomUUID()}", sourceType = DataSourceType.API, location = "https://github.com/fixture"))
        mvc.perform(auth(post("/api/data-sources/${source.id}/ingestions"))).andExpect(status().isForbidden)
    }

    @Test
    fun `platform admitted administration does not depend on duplicated group configuration`() {
        val (_, dataset) = fixture()
        val unrelatedGroup = "grp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        mvc.perform(auth(get("/api/v1/operator-capabilities"), group = unrelatedGroup))
            .andExpect(status().isOk).andExpect(jsonPath("$.manageGrants").value(true)).andExpect(jsonPath("$.writableDatasetIds.length()").value(0))
        mvc.perform(
            auth(
                put("/api/v1/dataset-grants/${dataset.id}").contentType(MediaType.APPLICATION_JSON)
                    .content("""{"principalId":"reader","permission":"READ"}"""),
                group = unrelatedGroup,
            ),
        ).andExpect(status().isNoContent)
        mvc.perform(auth(get("/api/datasets"), "reader", unrelatedGroup)).andExpect(jsonPath("$[0].id").value(dataset.id.toString()))
        mvc.perform(get("/api/v1/dataset-grants/${dataset.id}")).andExpect(status().isUnauthorized)
    }
}
