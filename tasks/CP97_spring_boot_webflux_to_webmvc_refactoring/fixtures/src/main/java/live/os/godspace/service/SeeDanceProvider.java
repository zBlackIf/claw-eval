package live.os.godspace.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import live.os.godspace.config.SeedanceProperties;
import live.os.godspace.model.ImageRatio;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class SeeDanceProvider implements VideoProvider {

    private static final Logger logger = LoggerFactory.getLogger(SeeDanceProvider.class);

    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    private final SeedanceProperties seedanceProperties;

    private static final String VIDEO_RESOLUTION = "480p";
    private static final String VIDEO_RATIO = "9:16";
    private static final int MIN_DURATION = 4;
    private static final int MAX_DURATION = 15;

    public SeeDanceProvider(SeedanceProperties seedanceProperties, ObjectMapper objectMapper) {
        this.seedanceProperties = seedanceProperties;
        this.objectMapper = objectMapper;
        this.webClient = WebClient.builder()
                .baseUrl(seedanceProperties.getBaseUrl())
                .defaultHeader("Content-Type", "application/json")
                .defaultHeader("Authorization", "Bearer " + seedanceProperties.getApiKey())
                .build();
    }

    @Override
    public String getName() {
        return "SeeDance";
    }

    @Override
    public String createImageTask(String prompt, ImageRatio imageRatio) {
        Map<String, Object> body = new HashMap<>();
        body.put("prompt", prompt);
        body.put("ratio", imageRatio.getValue());
        body.put("resolution", VIDEO_RESOLUTION);

        return webClient.post()
                .uri("/v1/images/generate")
                .bodyValue(body)
                .retrieve()
                .bodyToMono(String.class)
                .map(response -> {
                    try {
                        JsonNode node = objectMapper.readTree(response);
                        return node.get("data").get("task_id").asText();
                    } catch (Exception e) {
                        throw new RuntimeException("Failed to parse image task response", e);
                    }
                })
                .block();
    }

    @Override
    public String createImageTaskWithReference(String prompt, String referenceImageUrl, ImageRatio imageRatio) {
        Map<String, Object> body = new HashMap<>();
        body.put("prompt", prompt);
        body.put("reference_image", referenceImageUrl);
        body.put("ratio", imageRatio.getValue());

        return webClient.post()
                .uri("/v1/images/generate-with-reference")
                .bodyValue(body)
                .retrieve()
                .bodyToMono(String.class)
                .map(response -> {
                    try {
                        JsonNode node = objectMapper.readTree(response);
                        return node.get("data").get("task_id").asText();
                    } catch (Exception e) {
                        throw new RuntimeException("Failed to parse image task response", e);
                    }
                })
                .block();
    }

    @Override
    public String createVideoTask(String prompt, String characterImageUrl, String sceneImageUrl, Integer duration) {
        int clampedDuration = Math.max(MIN_DURATION, Math.min(MAX_DURATION, duration));

        Map<String, Object> body = new HashMap<>();
        body.put("prompt", prompt);
        body.put("character_image", characterImageUrl);
        body.put("scene_image", sceneImageUrl);
        body.put("duration", clampedDuration);
        body.put("resolution", VIDEO_RESOLUTION);
        body.put("ratio", VIDEO_RATIO);

        return webClient.post()
                .uri("/v1/videos/generate")
                .bodyValue(body)
                .retrieve()
                .bodyToMono(String.class)
                .map(response -> {
                    try {
                        JsonNode node = objectMapper.readTree(response);
                        return node.get("data").get("task_id").asText();
                    } catch (Exception e) {
                        throw new RuntimeException("Failed to parse video task response", e);
                    }
                })
                .block();
    }

    @Override
    public String pollVideoUntilComplete(String taskId) {
        return pollUntilComplete("/v1/videos/status/" + taskId, "video_url");
    }

    @Override
    public String createTransitionVideoTask(String prompt, String firstFrameUrl, String lastFrameUrl) {
        Map<String, Object> body = new HashMap<>();
        body.put("prompt", prompt);
        body.put("first_frame", firstFrameUrl);
        body.put("last_frame", lastFrameUrl);
        body.put("resolution", VIDEO_RESOLUTION);

        return webClient.post()
                .uri("/v1/videos/transition")
                .bodyValue(body)
                .retrieve()
                .bodyToMono(String.class)
                .map(response -> {
                    try {
                        JsonNode node = objectMapper.readTree(response);
                        return node.get("data").get("task_id").asText();
                    } catch (Exception e) {
                        throw new RuntimeException("Failed to parse transition task response", e);
                    }
                })
                .block();
    }

    @Override
    public String pollTransitionVideoUntilComplete(String taskId) {
        return pollUntilComplete("/v1/videos/transition/status/" + taskId, "video_url");
    }

    private String pollUntilComplete(String uri, String resultKey) {
        int maxAttempts = 120;
        return Mono.defer(() -> webClient.get()
                        .uri(uri)
                        .retrieve()
                        .bodyToMono(String.class))
                .flatMap(response -> {
                    try {
                        JsonNode node = objectMapper.readTree(response);
                        String status = node.get("data").get("status").asText();
                        if ("completed".equals(status)) {
                            return Mono.just(node.get("data").get(resultKey).asText());
                        } else if ("failed".equals(status)) {
                            String error = node.get("data").has("error")
                                    ? node.get("data").get("error").asText()
                                    : "Unknown error";
                            return Mono.error(new RuntimeException("Task failed: " + error));
                        }
                        return Mono.empty();
                    } catch (Exception e) {
                        return Mono.error(new RuntimeException("Failed to parse poll response", e));
                    }
                })
                .repeatWhenEmpty(maxAttempts, flux -> flux.delayElements(Duration.ofSeconds(3)))
                .subscribeOn(Schedulers.boundedElastic())
                .block(Duration.ofMinutes(10));
    }
}
