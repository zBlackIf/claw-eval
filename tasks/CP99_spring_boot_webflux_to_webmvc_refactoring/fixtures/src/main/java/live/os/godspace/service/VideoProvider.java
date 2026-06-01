package live.os.godspace.service;

import live.os.godspace.model.ImageRatio;

import java.util.List;

public interface VideoProvider {

    String getName();

    String createImageTask(String prompt, ImageRatio imageRatio);

    String createImageTaskWithReference(String prompt, String referenceImageUrl, ImageRatio imageRatio);

    String createVideoTask(String prompt, String characterImageUrl, String sceneImageUrl, Integer duration);

    String pollVideoUntilComplete(String taskId);

    String createTransitionVideoTask(String prompt, String firstFrameUrl, String lastFrameUrl);

    String pollTransitionVideoUntilComplete(String taskId);
}
