package bookstore;

import com.intuit.karate.Results;
import com.intuit.karate.Runner;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * JUnit 5 entry point for the Karate suite.
 *
 * Kept as a plain runner so the suite is driven by tags from CI
 * (`mvn test -Dkarate.options="--tags @smoke"`) rather than by editing Java.
 */
class BookStoreApiTest {

    @Test
    void runAll() {
        Results results = Runner.path("classpath:bookstore")
                .tags("~@ignore")          // reusable call-only features are excluded
                .outputCucumberJson(true)  // consumed by the CI reporter
                .outputJunitXml(true)      // per-scenario XML for the run summary
                .parallel(5);              // each scenario owns its own account, so this is safe
        assertEquals(0, results.getFailCount(), results.getErrorMessages());
    }
}
