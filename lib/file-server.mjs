import express from "express";

export const LOCAL_FILE_SERVER_PORT = 9002;
export const LOCAL_FILE_SERVER_URL = `http://127.0.0.1:${LOCAL_FILE_SERVER_PORT}`;

/**
 * Khởi động một server file cục bộ để API có thể truy cập tài nguyên
 * @param {string} baseDir - Thư mục gốc để phục vụ file
 * @returns {Promise<import('http').Server>} - Đối tượng server
 */
export function startFileServer(baseDir) {
  return new Promise((resolve) => {
    const app = express();
    app.use(express.static(baseDir));
    const server = app.listen(LOCAL_FILE_SERVER_PORT, () => {
      console.log(`🚀 Local file server started at ${LOCAL_FILE_SERVER_URL}`);
      console.log(`   Serving files from: ${baseDir}`);
      resolve(server);
    });
  });
}