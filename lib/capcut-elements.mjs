import fs from "fs";
import path from "path";
import { callApi, callApiGet } from "./api-client.mjs";
import { LOCAL_FILE_SERVER_URL } from "./file-server.mjs";

/**
 * Thêm track audio chính vào draft.
 * @param {string} draftId - ID của draft.
 * @param {string} audioPath - Đường dẫn file audio.
 * @param {string} baseServeDir - Thư mục gốc của file server.
 */
export async function addAudioTrack(draftId, audioPath, baseServeDir) {
  const audioUrl = `${LOCAL_FILE_SERVER_URL}/${path
    .relative(baseServeDir, audioPath)
    .replace(/\\/g, "/")}`;
  await callApi("/add_audio", {
    draft_id: draftId,
    audio_url: audioUrl,
    start: 0,
  });
}

/**
 * Thêm lớp nền mờ vào draft.
 * @param {string} draftId - ID của draft.
 * @param {object} scriptData - Dữ liệu từ capcut-api.json.
 * @param {number} totalAudioDuration - Tổng thời lượng audio.
 * @param {string} baseServeDir - Thư mục gốc của file server.
 */
export async function addBackgroundLayer(
  draftId,
  scriptData,
  totalAudioDuration,
  baseServeDir
) {
  const params = scriptData.generation_params?.background_layer || {
    scale: 2.5,
    blur: 3,
  };
  if (
    !scriptData.scenes ||
    scriptData.scenes.length === 0 ||
    !scriptData.scenes[0].image
  ) {
    console.log(
      "⏩ Skipping background layer: No scenes or first scene has no image."
    );
    return;
  }

  console.log("🎨 Adding background layer...");
  const backgroundImagePath = scriptData.scenes[0].image;
  const backgroundImageUrl = `${LOCAL_FILE_SERVER_URL}/${path
    .relative(baseServeDir, backgroundImagePath)
    .replace(/\\/g, "/")}`;

  await callApi("/add_video", {
    draft_id: draftId,
    video_url: backgroundImageUrl,
    start: Math.round(0),
    end: Math.round(totalAudioDuration),
    track_name: "background_track",
    relative_index: -1,
    scale_x: params.scale,
    scale_y: params.scale,
    background_blur: params.blur,
  });
  console.log("✅ Background layer added.");
}

/**
 * Thêm các hình ảnh của từng scene vào main_track.
 * @param {string} draftId - ID của draft.
 * @param {object} scriptData - Dữ liệu từ capcut-api.json.
 * @param {number} totalAudioDuration - Tổng thời lượng audio.
 * @param {string} baseServeDir - Thư mục gốc của file server.
 */
export async function addImageScenes(
  draftId,
  scriptData,
  totalAudioDuration,
  baseServeDir
) {
  const params = scriptData.generation_params?.scene_images || { scale: 1.2 };
  const totalVisualDuration = scriptData.scenes.reduce(
    (sum, scene) => sum + (scene.end - scene.start),
    0
  );
  const stretchFactor =
    totalVisualDuration > 0 ? totalAudioDuration / totalVisualDuration : 1;
  let currentTime = 0;

  for (const [index, scene] of scriptData.scenes.entries()) {
    if (scene.start === null || scene.end === null || !scene.image) {
      console.warn(
        `⚠️ Skipping scene ${index + 1}: Missing time or image information.`
      );
      continue;
    }

    const imageUrl = `${LOCAL_FILE_SERVER_URL}/${path
      .relative(baseServeDir, scene.image)
      .replace(/\\/g, "/")}`;

    const originalDuration = scene.end - scene.start;
    const newDuration = originalDuration * stretchFactor;

    await callApi("/add_image", {
      draft_id: draftId,
      image_url: imageUrl,
      start: Math.round(currentTime),
      end: Math.round(currentTime + newDuration),
      track_name: "main_track",
      relative_index: 9,
      scale_x: params.scale,
      scale_y: params.scale,
    });

    currentTime += newDuration;
  }
}

/**
 * Thêm các hiệu ứng video ngẫu nhiên vào draft.
 * @param {string} draftId - ID của draft.
 * @param {number} totalAudioDuration - Tổng thời lượng audio.
 * @param {number} width - Chiều rộng của video.
 * @param {number} height - Chiều cao của video.
 */
export async function addRandomEffects(
  draftId,
  totalAudioDuration,
  width,
  height
) {
  try {
    console.log("✨ Fetching available video effects...");
    const useFetchApi = false; // Đặt thành true để gọi API lấy danh sách effect
    let availableEffects = [
      "Feathers", // Lông vũ (như bạn đã đề cập)
      "Butterflies", // Bươm bướm
      "Butterfly_Dream", // Giấc mơ bươm bướm
      "Gleam", // Ánh sáng lấp lánh
      "Spark", // Tia lửa nhỏ
      "Spark_2", // Tia lửa nhỏ 2
      "Star", // Ngôi sao
      "Mini_Stars", // Những ngôi sao nhỏ
      "Mini_stars_II", // Những ngôi sao nhỏ II
      "Starry", // Đầy sao
      "Starlight", // Ánh sao
      "Astral", // Tinh tú, vũ trụ
      "Meteor", // Sao băng
      "Fireworks_2", // Pháo hoa 2
      "Firefly", // Đom đóm
      "By_the_Fireplace", // Bên lò sưởi
      "Sun", // Mặt trời
      "Leak_1", // Rò rỉ ánh sáng 1
      "Leak_2", // Rò rỉ ánh sáng 2
      "Halo", // Hào quang
      "Halo_2", // Hào quang 2
      "Edge_Glow", // Viền phát sáng
      "Soft", // Mềm mại
      "Blur", // Làm mờ
      "Blurry_Focus", // Lấy nét mờ
      "Hazy", // Mờ ảo
      "Vignette", // Hiệu ứng tối góc
      "Fuzzy", // Mờ mịn
      "Frosted_Quality", // Chất lượng mờ sương
      "Ripple", // Gợn sóng
      "Heart_Kisses", // Nụ hôn trái tim
      "Girls_Secrets", // Bí mật của các cô gái
      "Radiating_Love", // Tỏa ra tình yêu
      "Lovestruck", // Say đắm
      "In_My_Heart", // Trong trái tim tôi
      "Heart_Background", // Nền trái tim
      "Pink_Hearts", // Trái tim hồng
      "Heart_Disco", // Vũ điệu trái tim
      "Heartbeat", // Nhịp đập trái tim
      "Bubbles_2", // Bong bóng 2
      "Snowflakes", // Bông tuyết
      "Snowfall", // Tuyết rơi
      "Rain", // Mưa
      "Mist", // Sương mù
      "Tree_Shade", // Bóng cây
      "Cherry_Blossom", // Hoa anh đào
      "Wonderland", // Xứ sở thần tiên
    ];

    if (useFetchApi) {
      const effectsResponse = await callApiGet("/get_video_scene_effect_types");
      availableEffects = effectsResponse?.output?.map((e) => e.name) || [];
    }

    if (availableEffects.length > 0) {
      console.log(
        `🪄 Found ${availableEffects.length} effects. Adding them randomly...`
      );
      const EFFECT_DURATION = 10; // Mỗi effect có thời lượng 5 giây
      const EFFECT_GAP = 0; // Khoảng nghỉ giữa các effect (tính bằng giây)
      const EFFECT_INTERVAL = EFFECT_DURATION + EFFECT_GAP; // Tính toán khoảng cách giữa các lần thêm
      const MAX_EFFECTS = 30; // Số lượng effect tối đa để thêm (đặt là 1 để test)
      let effectsAdded = 0;
      const addedEffectNames = []; // Mảng để lưu tên các effect đã thêm

      for (
        let currentTime = 0;
        currentTime < totalAudioDuration && effectsAdded < MAX_EFFECTS;
        currentTime += EFFECT_INTERVAL
      ) {
        const effectStart = currentTime;
        const effectEnd = Math.min(
          effectStart + EFFECT_DURATION,
          totalAudioDuration
        );
        // Bỏ qua nếu effect quá ngắn hoặc nằm ngoài video
        if (effectEnd <= effectStart) {
          break;
        }

        // Chọn một effect ngẫu nhiên từ danh sách
        const randomEffect =
          availableEffects[Math.floor(Math.random() * availableEffects.length)];
        addedEffectNames.push(randomEffect); // Thêm tên effect vào danh sách

        console.log(
          `Adding effect "${randomEffect}" from ${effectStart.toFixed(
            2
          )}s to ${effectEnd.toFixed(2)}s`
        );

        await callApi("/add_effect", {
          draft_id: draftId,
          effect_type: randomEffect, // Sử dụng lại hiệu ứng ngẫu nhiên đã chọn
          start: Math.round(effectStart),
          end: Math.round(effectEnd),
          track_name: "effect_track",
          relative_index: 10, // Đảm bảo effect nằm trên lớp hình ảnh
          params: [],
          width,
          height,
        });
        effectsAdded++;
      }
      console.log(
        `✅ Random effects added. List: [${addedEffectNames.join(", ")}]`
      );
    }
  } catch (err) {
    console.warn("⚠️ Could not add random effects:", err.message);
  }
}

/**
 * Thêm các hiệu ứng cố định được định nghĩa trong file JSON.
 * @param {string} draftId - ID của draft.
 * @param {object} scriptData - Dữ liệu từ capcut-api.json.
 * @param {number} totalAudioDuration - Tổng thời lượng audio.
 * @param {number} width - Chiều rộng của video.
 * @param {number} height - Chiều cao của video.
 */
export async function addFixedEffects(
  draftId,
  scriptData,
  totalAudioDuration,
  width,
  height
) {
  const effectsList = scriptData.generation_params?.fixed_effects?.effects;

  if (!effectsList || !Array.isArray(effectsList) || effectsList.length === 0) {
    console.log(
      "⏩ Skipping fixed effects: No 'fixed_effects.effects' array found in generation_params or it is empty."
    );
    return;
  }

  console.log("✨ Adding fixed effects from JSON...");

  for (const effect of effectsList) {
    if (!effect.effect_type) {
      console.warn("⚠️ Skipping a fixed effect: 'effect_type' is missing.");
      continue;
    }

    console.log(
      `   - Adding fixed effect "${effect.effect_type}" for the full duration.`
    );
    await callApi("/add_effect", {
      draft_id: draftId,
      effect_type: effect.effect_type,
      start: Math.round(0),
      end: Math.round(totalAudioDuration),
      track_name: effect.track_name || "fixed_effects_track",
      // Đặt ở lớp thấp (trên lớp nền) để không che các hiệu ứng chính
      relative_index: 1,
      params: effect.params || [],
      width,
      height,
    });
  }
  console.log("✅ Fixed effects added.");
}

/**
 * Thêm logo vào góc video.
 * @param {string} draftId - ID của draft.
 * @param {object} scriptData - Dữ liệu từ capcut-api.json.
 * @param {number} totalAudioDuration - Tổng thời lượng audio.
 * @param {string} baseServeDir - Thư mục gốc của file server.
 */
export async function addLogo(
  draftId,
  scriptData,
  totalAudioDuration,
  baseServeDir
) {
  const params = scriptData.generation_params?.logo;
  const logoPath = params?.path;
  if (!fs.existsSync(logoPath)) {
    console.warn(`⚠️ Logo file not found, skipping: ${logoPath}`);
    return;
  }

  console.log("🖼️  Adding logo...");
  const logoUrl = `${LOCAL_FILE_SERVER_URL}/${path
    .relative(baseServeDir, logoPath)
    .replace(/\\/g, "/")}`;

  await callApi("/add_image", {
    draft_id: draftId,
    image_url: logoUrl,
    start: Math.round(0),
    end: Math.round(totalAudioDuration),
    track_name: "logo_track",
    relative_index: 20, // Đặt ở lớp trên cùng để luôn hiển thị
    scale_x: params.scale || 0.1,
    scale_y: params.scale || 0.1,
    transform_x: params.transform_x || 0.9,
    transform_y: params.transform_y || -0.5,
  });

  console.log("✅ Logo added.");
}

/**
 * Thêm logo dạng text vào video.
 * @param {string} draftId - ID của draft.
 * @param {object} scriptData - Dữ liệu từ capcut-api.json.
 * @param {number} totalAudioDuration - Tổng thời lượng audio.
 */
export async function addTextLogo(draftId, scriptData, totalAudioDuration) {
  const params = scriptData.generation_params?.text_logo;

  if (!params?.text) {
    console.log(
      "⏩ Skipping text logo: 'text' property is missing in 'text_logo' config."
    );
    return;
  }

  console.log(`✍️  Adding text logo: "${params.text}"`);

  // Sử dụng toán tử ?? để cung cấp giá trị mặc định an toàn
  await callApi("/add_text", {
    text: params.text,
    draft_id: draftId,
    start: Math.round(params.start ?? 0),
    end: Math.round(params.end ?? totalAudioDuration),
    font_size: params.font_size ?? 12,
    font_color: params.font_color ?? "#FFFFFF",
    font_alpha: params.font_alpha ?? 0.6,
    transform_x: params.transform_x ?? 0,
    transform_y: params.transform_y ?? 0,
  });

  console.log("✅ Text logo added.");
}