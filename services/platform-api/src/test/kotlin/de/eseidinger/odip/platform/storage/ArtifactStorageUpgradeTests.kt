package de.eseidinger.odip.platform.storage

import de.eseidinger.odip.platform.publication.sha256
import org.flywaydb.core.Flyway
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.dao.DataAccessException
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.datasource.SingleConnectionDataSource
import java.util.UUID
import javax.sql.DataSource
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

@SpringBootTest
class ArtifactStorageUpgradeTests(@Autowired private val dataSource: DataSource) {
    @Test fun `V13 upgrades a V12 database with published artifacts without weakening immutability`() {
        val schema = "storage_upgrade_${UUID.randomUUID().toString().replace("-", "")}"
        dataSource.connection.use { connection ->
            val scoped = SingleConnectionDataSource(connection, true)
            val jdbc = JdbcTemplate(scoped)
            try {
                Flyway.configure().dataSource(scoped).schemas(schema).defaultSchema(schema).target("12").load().migrate()
                connection.schema = schema
                val dataset = UUID.randomUUID()
                val publication = UUID.randomUUID()
                val source = UUID.randomUUID()
                val run = UUID.randomUUID()
                val raw = UUID.randomUUID()
                val bytes = "existing immutable bytes".toByteArray()
                val manifest = "{}".toByteArray()
                jdbc.update("INSERT INTO dataset(id,name) VALUES (?,'Existing dataset')", dataset)
                jdbc.update("INSERT INTO data_source(id,name,source_type,location) VALUES (?,'Existing source','API','https://example.test')", source)
                jdbc.update("INSERT INTO pipeline_run(id,pipeline_name,source_id,status) VALUES (?,'existing',?,'SUCCEEDED')", run, source)
                jdbc.update("INSERT INTO raw_artifact(id,pipeline_run_id,source_id,storage_uri,payload,content_length,checksum_sha256,retrieved_at) VALUES (?,?,?,'postgres://existing',?,?,?,CURRENT_TIMESTAMP)", raw, run, source, bytes, bytes.size, sha256(bytes))
                jdbc.update("INSERT INTO dataset_publication(id,dataset_id,public_dataset_id,version,manifest,manifest_sha256,status,creator,idempotency_key,request_sha256) VALUES (?,?,'existing','1.0.0',?,?,'DRAFT','writer','existing',?)", publication, dataset, manifest, sha256(manifest), sha256(manifest))
                jdbc.update("INSERT INTO publication_artifact VALUES (?,'existing',?,?)", publication, bytes, sha256(bytes))
                jdbc.update("INSERT INTO publication_input VALUES (?,?)", publication, raw)
                jdbc.update("UPDATE dataset_publication SET status='PUBLISHED' WHERE id=?", publication)

                Flyway.configure().dataSource(scoped).schemas(schema).defaultSchema(schema).load().migrate()
                connection.schema = schema
                assertContentEquals(bytes, jdbc.queryForObject("SELECT payload FROM publication_artifact WHERE publication_id=?", ByteArray::class.java, publication))
                assertContentEquals(manifest, jdbc.queryForObject("SELECT manifest FROM dataset_publication WHERE id=?", ByteArray::class.java, publication))
                assertContentEquals(bytes, jdbc.queryForObject("SELECT payload FROM raw_artifact WHERE id=?", ByteArray::class.java, raw))
                assertEquals(bytes.size, jdbc.queryForObject("SELECT COALESCE(content_length,octet_length(payload)) FROM publication_artifact WHERE publication_id=?", Int::class.java, publication))
                assertFailsWith<DataAccessException> { jdbc.update("UPDATE publication_artifact SET payload='changed'::bytea WHERE publication_id=?", publication) }
                assertFailsWith<DataAccessException> { jdbc.update("UPDATE raw_artifact SET payload='changed'::bytea WHERE id=?", raw) }
                assertFailsWith<DataAccessException> { jdbc.update("DELETE FROM publication_input WHERE publication_id=?", publication) }
            } finally {
                connection.schema = "public"
                jdbc.execute("DROP SCHEMA IF EXISTS $schema CASCADE")
            }
        }
    }
}
