package live.os.godspace.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import live.os.godspace.config.WanxiangProperties;
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
public class WanxiangVideoProvider implements VideoProvider {

    private static final Logger logger = LoggerFactory.getLogger(WanxiangVideoProvider.class);

    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    private final WanxiangProperties wanxiangProperties;

    public WanxiangVideoProvider(WanxiangProperties wanxiangProperties, ObjectMapper objectMapper) {
        this.wanxiangProperties = wanxiangProperties;
        this.objectMapper = objectMapper;
        this.webClient = WebClient.builder()
                .baseUrl(wanxiangProperties.getBaseUrl())
                .defaultHeader("Content-Type", "application/json")
                .build();
    }

    @Override
    public String getName() {
        return "Wanxiang";
    }

    @Override
    public String createImageTask(String prompt, ImageRatio imageRatio) {
        Map<String, Object> body = new HashMap<>();
        body.put("model", wanxiangProperties.getModel());
        body.put("input", Map.of("prompt", prompt));
        body.put("parameters", Map.of(
                "size", imageRatio.getWanxiangSize(),
                "n", 1
        ));

        String responseBody = webClient.post()
                .uri("/api/v1/services/aigc/text2image/image-synthesis")
                .header("Authorization", "Bearer " + wanxiangProperties.getApiKey())
                .bodyValue(body)
                .retrieve()
                .bodyToMono(String.class)
                .block();

        try {
            JsonNode node = objectMapper.readTree(responseBody);
            return node.get("output").get("task_id").asText();
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse Wanxiang image task response", e);
        }
    }

    @Override
    public String createImageTaskWithReference(String prompt, String referenceImageUrl, ImageRatio imageRatio) {
        Map<String, Object> body = new HashMap<>();
        body.put("model", wanxiangProperties.getModel());
        body.put("input", Map.of("prompt", prompt, "ref_img", referenceImageUrl));
        body.put("parameters", Map.of("size", imageRatio.getWanxiangSize()));

        String responseBody = webClient.post()
                .uri("/api/v1/services/aigc/text2image/image-synthesis")
                .header("Authorization", "Bearer " + wanxiangProperties.getApiKey())
                .bodyValue(body)
                .retrieve()
                .bodyToMono(String.class)
                .block();

        try {
            JsonNode node = objectMapper.readTree(responseBody);
            return node.get("output").get("task_id").asText();
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse Wanxiang image reference task response", e);
        }
    }

    @Override
    public String createVideoTask(String prompt, String characterImageUrl, String sceneImageUrl, Integer duration) {
        Map<String, Object> input = new HashMap<>();
        input.put("prompt", prompt);
        input.put("img_url", characterImageUrl);

        Map<String, Object> body = new HashMap<>();
        body.put("model", wanxiangProperties.getVideoModel());
        body.put("input", input);
        body.put("parameters", Map.of("duration", duration));

        String responseBody = webClient.post()
                .uri("/api/v1/services/aigc/video/video-synthesis")
                .header("Authorization", "Bearer " + wanxiangProperties.getApiKey())
                .bodyValue(body)
                .retrieve()
                .bodyToMono(String.class)
                .block();

        try {
            JsonNode node = objectMapper.readTree(responseBody);
            return node.get("output").get("task_id").asText();
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse Wanxiang video task response", e);
        }
    }

    @Override
    public String pollVideoUntilComplete(String taskId) {
        return pollTaskResult(taskId, "video_url");
    }

    @Override
    public String createTransitionVideoTask(String prompt, String firstFrameUrl, String lastFrameUrl) {
        Map<String, Object> input = new HashMap<>();
        input.put("prompt", prompt);
        input.put("first_frame_url", firstFrameUrl);
        input.put("last_frame_url", lastFrameUrl);

        Map<String, Object> body = new HashMap<>();
        body.put("model", wanxiangProperties.getVideoModel());
        body.put("input", input);

        String responseBody = webClient.post()
                .uri("/api/v1/services/aigc/video/video-transition")
                .header("Authorization", "Bearer " + wanxiangProperties.getApiKey())
                .bodyValue(body)
                .retrieve()
                .bodyToMono(String.class)
                .block();

        try {
            JsonNode node = objectMapper.readTree(responseBody);
            return node.get("output").get("task_id").asText();
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse Wanxiang transition task response", e);
        }
    }

    @Override
    public String pollTransitionVideoUntilComplete(String taskId) {
        return pollTaskResult(taskId, "video_url");
    }

    private String pollTaskResult(String taskId, String resultKey) {
        int maxRetries = 120;
        return Mono.defer(() -> webClient.get()
                        .uri("/api/v1/tasks/" + taskId)
                        .header("Authorization", "Bearer " + wanxiangProperties.getApiKey())
                        .retrieve()
                        .bodyToMono(String.class))
                .flatMap(response -> {
                    try {
                        JsonNode node = objectMapper.readTree(response);
                        String status = node.get("output").get("task_status").asText();
                        if ("SUCCEEDED".equals(status)) {
                            JsonNode results = node.get("output").get("results");
                            if (results.isArray() && results.size() > 0) {
                                return Mono.just(results.get(0).get(resultKey).asText());
                            }
                            return Mono.error(new RuntimeException("No results in completed task"));
                        } else if ("FAILED".equals(status)) {
                            String msg = node.has("message") ? node.get("message").asText() : "Unknown error";
                            return Mono.error(new RuntimeException("Task failed: " + msg));
                        }
                        return Mono.empty();
                    } catch (Exception e) {
                        return Mono.error(new RuntimeException("Failed to parse Wanxiang poll response", e));
                    }
                })
                .repeatWhenEmpty(maxRetries, flux -> flux.delayElements(Duration.ofSeconds(3)))
                .subscribeOn(Schedulers.boundedElastic())
                .block(Duration.ofMinutes(10));
    }
}
