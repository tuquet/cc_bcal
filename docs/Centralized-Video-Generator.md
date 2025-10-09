# 🎬 Video Generator - Centralized Architecture

## ✅ NEW: Centralized Approach (Recommended)

### Single Tool: `video-generator.mjs`
- **No more scattered .bat files** across episode folders
- **Single source of truth** for video generation
- **Better error handling** với auto-overwrite (-y flag)
- **Cross-platform** support

## 📋 Commands

```bash
# Direct usage
node video-generator.mjs test 1      # Test video
node video-generator.mjs final 1     # Final video với Ken Burns
node video-generator.mjs all 1       # Both test & final
node video-generator.mjs batch 1,2,3 # Multiple episodes

# NPM Scripts (recommended)
npm run video:test 1
npm run video:final 1
npm run video:all 1
npm run video:batch 1,2,3
```

## 🔄 Complete Workflow: JSON → Video

```bash
# 1. Generate episodes từ JSON data
npm run generate

# 2. Setup production folders
npm run prepare 1

# 3. Add assets manually:
#    - episodes/1.xxx/audio/voiceover.mp3  
#    - episodes/1.xxx/images/1.png → 5.png

# 4. Generate videos
npm run video:all 1
```

## 📊 Architecture Comparison

| Feature | OLD (.bat approach) | NEW (Centralized) |
|---------|-------------------|-------------------|
| **Maintenance** | ❌ Files everywhere | ✅ Single tool |
| **Error Handling** | ❌ Manual overwrite prompts | ✅ Auto overwrite |
| **Portability** | ❌ OS-specific .bat files | ✅ Cross-platform Node.js |
| **Debugging** | ❌ Hard to track issues | ✅ Centralized logging |
| **Scalability** | ❌ N files for N episodes | ✅ 1 tool for all episodes |

## 🧹 Migration Steps

### Files to REMOVE:
- `generate-video-commands.mjs` (deprecated)
- All `.bat` files in episode folders
- All `.sh` files in episode folders

### Files to KEEP:
- ✅ `video-generator.mjs` (NEW centralized tool)
- ✅ `run.mjs` (JSON structure generation)  
- ✅ `prepare-episode.mjs` (folder setup)

### Package.json Updates:
```json
{
  "scripts": {
    "video:test": "node video-generator.mjs test",
    "video:final": "node video-generator.mjs final",
    "video:all": "node video-generator.mjs all",
    "video:batch": "node video-generator.mjs batch"
  }
}
```

## 🎯 Best Practices

1. **Always use npm scripts** instead of direct node commands
2. **Test video first** để verify audio/image assets
3. **Use batch mode** cho multiple episodes
4. **Follow folder structure** conventions

## 🔧 Technical Features

### Ken Burns Effects:
- Zoom: 1.0 → 1.5 với smooth transition
- Center-crop from 1024x1024 → 1920x1080
- Duration: Configurable via timing.json

### Error Handling:
- Auto-overwrite existing videos (-y flag)
- Path validation
- Asset existence checks
- Clear error messages

### Performance:
- FFmpeg-static integration
- Parallel processing capability
- Memory-efficient operations

---

## 🎉 Result

**Before:** Scattered .bat files, manual overwrite prompts, OS-dependent scripts  
**After:** Single centralized tool, auto-overwrite, cross-platform compatibility

**Benefit:** Cleaner architecture, easier maintenance, better user experience