import fetch from "node-fetch";

const API_BASE_URL = "http://127.0.0.1:9001";

/**
 * Hàm helper để gọi API và xử lý lỗi
 * @param {string} endpoint - Endpoint của API (ví dụ: /create_draft)
 * @param {object} body - Payload gửi đi
 * @returns {Promise<object>} - Dữ liệu JSON trả về từ API
 */
export async function callApi(endpoint, body) {
  console.log(`📞 Calling API: ${endpoint}`);
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `API call failed with status ${response.status}: ${errorText}`
      );
    }

    const result = await response.json();
    console.log(`✅ Success: ${endpoint}`);
    return result;
  } catch (error) {
    console.error(`❌ Error calling ${endpoint}:`, error.message);
    throw error; // Ném lỗi để dừng pipeline
  }
}

/**
 * Hàm helper để gọi API GET và xử lý lỗi
 * @param {string} endpoint - Endpoint của API (ví dụ: /get_video_scene_effect_types)
 * @returns {Promise<object>} - Dữ liệu JSON trả về từ API
 */
export async function callApiGet(endpoint) {
  console.log(`📞 Calling API (GET): ${endpoint}`);
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `API call failed with status ${response.status}: ${errorText}`
      );
    }

    const result = await response.json();
    console.log(`✅ Success (GET): ${endpoint}`);
    return result;
  } catch (error) {
    console.error(`❌ Error calling (GET) ${endpoint}:`, error.message);
    throw error; // Ném lỗi để dừng pipeline
  }
}