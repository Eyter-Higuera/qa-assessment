package bookstore;

import com.intuit.karate.Results;
import com.intuit.karate.Runner;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/** The subset that gates every deployment - fast, and it must never be flaky. */
class SmokeTest {

    @Test
    void runSmoke() {
        Results results = Runner.path("classpath:bookstore")
                .tags("@smoke", "~@ignore")
                .outputCucumberJson(true)
                .parallel(3);
        assertEquals(0, results.getFailCount(), results.getErrorMessages());
    }
}
