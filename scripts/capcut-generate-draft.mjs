import fs from "fs";
import path from "path";
import { homedir } from "os";
import { fileURLToPath } from "url";
import { callApi } from "../lib/api-client.mjs";
import { startFileServer } from "../lib/file-server.mjs";
import {
  addAudioTrack,
  addBackgroundLayer,
  addImageScenes,
  addRandomEffects,
  addFixedEffects,
  addLogo,
  addTextLogo,
} from "../lib/capcut-elements.mjs";

/**
 * Lớp quản lý việc tạo video CapCut.
 */
class CapCutGenerator {
  constructor(episodeDir, ratio = "9:16") {
    this.episodeDir = episodeDir;
    this.ratio = ratio;
    this.fileServer = null;
    this.draftId = null;
    this.scriptData = null;
    this.totalAudioDuration = 0;
    this.width = 0;
    this.height = 0;
    this.baseServeDir = path.resolve(episodeDir, "..", "..");
  }
  
  /**
   * Khởi tạo và kiểm tra các file cần thiết.
   */
  async init() {
    if (!fs.existsSync(this.episodeDir)) {
      throw new Error(`❌ Thư mục episode không tồn tại: ${this.episodeDir}`);
    }

    const scriptJsonPath = path.join(this.episodeDir, "capcut-api.json");
    this.audioPath = path.join(this.episodeDir, "audio.mp3");

    if (!fs.existsSync(scriptJsonPath)) {
      throw new Error(
        `❌ Không tìm thấy file capcut-api.json trong: ${this.episodeDir}`
      );
    }
    if (!fs.existsSync(this.audioPath)) {
      throw new Error(
        `❌ Không tìm thấy file audio.mp3 trong: ${this.episodeDir}`
      );
    }

    this.scriptData = JSON.parse(fs.readFileSync(scriptJsonPath, "utf8"));
    this.totalAudioDuration =
      Math.round(this.scriptData.duration * 1000) / 1000;

    const dimensions = {
      "9:16": { width: 1080, height: 1920 },
      "16:9": { width: 1920, height: 1080 },
    };
    const { width, height } = dimensions[this.ratio] || dimensions["16:9"];
    this.width = width;
    this.height = height;
  }
  
  /**
   * Chạy toàn bộ pipeline tạo video.
   */
  async run() {
    try {
      await this.init();
      this.fileServer = await startFileServer(this.baseServeDir);

      console.log( 
        `🎬 Creating draft with ratio ${this.ratio} (${this.width}x${this.height})`
      );

      // --- BƯỚC 1: TẠO DRAFT ---
      const createDraftResponse = await callApi("/create_draft", {
        width: this.width,
        height: this.height,
      });
      this.draftId = createDraftResponse?.output?.draft_id;
      console.log(`🎉 Draft đã được tạo với ID: ${this.draftId}`);
      
      // --- BƯỚC 2: THÊM AUDIO ---
      // Audio là thành phần cốt lõi, luôn được thêm vào
      await addAudioTrack(this.draftId, this.audioPath, this.baseServeDir);

      const enabledModules =
        this.scriptData.generation_params?.enabled_modules || [];

      const runIfEnabled = async (moduleName, action, ...args) => {
        if (enabledModules.includes(moduleName)) {
          console.log(`✅ Module '${moduleName}' is enabled. Running...`);
          await action(...args);
        } else {
          console.log(
            `⏩ Skipping module '${moduleName}': Not found in 'enabled_modules'.`
          );
        }
      };

      // --- BƯỚC 3: THÊM CÁC LỚP HÌNH ẢNH ---
      await runIfEnabled(
        "background_layer",
        addBackgroundLayer,
        this.draftId,
        this.scriptData,
        this.totalAudioDuration,
        this.baseServeDir
      );

      await runIfEnabled(
        "scene_images",
        addImageScenes,
        this.draftId,
        this.scriptData,
        this.totalAudioDuration,
        this.baseServeDir
      );
      
      // --- BƯỚC 4: THÊM LOGO & TEXT ---
      await runIfEnabled(
        "logo",
        addLogo,
        this.draftId,
        this.scriptData,
        this.totalAudioDuration,
        this.baseServeDir
      );

      await runIfEnabled(
        "text_logo",
        addTextLogo,
        this.draftId,
        this.scriptData,
        this.totalAudioDuration
      );
      
      // --- BƯỚC 5: THÊM EFFECTS ---
      await runIfEnabled(
        "fixed_effects",
        addFixedEffects,
        this.draftId,
        this.scriptData,
        this.totalAudioDuration,
        this.width,
        this.height
      );
      
      await runIfEnabled(
        "random_effects",
        addRandomEffects,
        this.draftId,
        this.totalAudioDuration,
        this.width,
        this.height
      );
      
      // --- BƯỚC 6: LƯU DRAFT ---
      await this.saveDraft();
      
      console.log("\n\n✨✨✨ PIPELINE HOÀN TẤT! ✨✨✨");
    } catch (error) {
      console.error("\n💥💥💥 PIPELINE THẤT BẠI! 💥💥💥");
      console.error("Đã xảy ra lỗi trong quá trình thực thi:", error.message);
    } finally {
      if (this.fileServer) {
        this.fileServer.close(() => {
          console.log("🔌 Local file server stopped.");
        });
      }
    }
  }
  
  /**
   * Lưu draft vào thư mục của CapCut.
   */
  async saveDraft() {
    const savePayload = {
      draft_id: this.draftId,
      draft_folder: path.join(
        homedir(),
        "AppData",
        "Local",
        "CapCut",
        "User Data",
        "Projects",
        "com.lveditor.draft"
      ),
    };

    const saveResponse = await callApi("/save_draft", savePayload);
    const finalDraftPath = path.join(savePayload.draft_folder, this.draftId);
    const folderUrl = `file://${finalDraftPath.replace(/\\/g, "/")}`;
    console.log(`✅ Draft đã được lưu. Mở thư mục: ${folderUrl}`);

    const draftUrl = saveResponse?.output?.draft_url;
    console.log("Draft URL (nếu có):", draftUrl);
  }
}

// --- CÁCH SỬ DỤNG ---
// Lấy đường dẫn thư mục episode từ tham số dòng lệnh
// Ví dụ: node scripts/capcut-generate-draft.mjs episodes/11.la-rung-vo-thuong --ratio 16:9
async function main() {
  const args = process.argv.slice(2);
  const targetEpisodeDir = args.find((arg) => !arg.startsWith("--"));
  const ratioArg = args.find((arg) => arg.startsWith("--ratio="));
  const ratio = ratioArg ? ratioArg.split("=")[1] : "9:16";

  if (!targetEpisodeDir) {
    const scriptName = path.basename(fileURLToPath(import.meta.url));
    console.error("❌ Vui lòng cung cấp đường dẫn đến thư mục episode.");
    console.error(
      `Ví dụ: node scripts/${scriptName} episodes/11.la-rung-vo-thuong`
    );
    console.error(`Tùy chọn: --ratio=16:9 (mặc định là 9:16)`);
    process.exit(1);
  }

  if (ratio !== "9:16" && ratio !== "16:9") {
    console.error(
      `❌ Tỉ lệ không hợp lệ: ${ratio}. Chỉ hỗ trợ '9:16' hoặc '16:9'.`
    );
    process.exit(1);
  }

  const generator = new CapCutGenerator(path.resolve(targetEpisodeDir), ratio);
  await generator.run();
}

main();
