/**
 * @file header.js
 * @author Aurorp1g
 * @brief 锐捷 ePortal 登录 POST Header 生成器
 * @description 用于生成校园网登录请求的 POST Header，包含Cookie构建、URL解析等功能
 */

var fs = require('fs');
var path = require('path');
var paths = require('./paths');

var args = process.argv.slice(2);
var isDebug = args.indexOf('--debug') !== -1;

/**
 * @brief 调试日志输出函数
 * @description 仅在debug模式下输出日志到控制台
 */
function log() {
    if (isDebug) {
        console.log.apply(console, arguments);
    }
}

var bodyModule;
try {
    bodyModule = require('./body.js');
} catch (e) {
    if (isDebug) console.warn("无法加载 body.js 模块:", e.message);
    bodyModule = null;
}

/**
 * @brief 生成POST请求头
 * @description 根据配置信息生成锐捷ePortal登录所需的HTTP请求头
 * @param {Object} config - 配置对象
 * @param {string} config.serverIp - 服务器IP地址
 * @param {string} config.queryString - 查询字符串
 * @param {string} config.getUrl - 完整URL
 * @param {string} config.userAgent - 用户代理字符串
 * @param {number} config.contentLength - 内容长度
 * @param {string} config.username - 用户名
 * @param {string} config.password - 密码
 * @param {string} config.service - 服务类型
 * @param {string} config.jsessionid - Session ID
 * @param {Object} config.postParams - POST参数（用于自动计算contentLength）
 * @returns {Object} HTTP请求头对象
 */
function generatePostHeader(config) {
    var serverIp = config.serverIp || "";
    var queryString = config.queryString || "";
    var getUrl = config.getUrl || "";
    var userAgent = config.userAgent || "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36 Edg/140.0.0.0";
    var contentLength = config.contentLength || 0;
    
    var username = config.username || "";
    var password = config.password || "";
    var service = config.service || "";
    var jsessionid = config.jsessionid || "";

    if (contentLength === 0 && bodyModule && config.postParams) {
        var postDataResult = bodyModule.generateLoginPostData(config.postParams);
        contentLength = postDataResult.postData.length;
    }

    var cookieString = buildCookieString({
        username: username,
        password: password,
        service: service,
        jsessionid: jsessionid
    });

    var host = extractHost(serverIp);
    var origin = serverIp;
    var referer = buildReferer(serverIp, queryString, getUrl);

    var header = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Connection": "keep-alive",
        "Content-Length": String(contentLength),
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookieString,
        "Host": host,
        "Origin": origin,
        "Referer": referer,
        "User-Agent": userAgent
    };

    return header;
}

/**
 * @brief 从URL中提取主机名
 * @description 解析URL并提取主机部分
 * @param {string} url - 输入的URL字符串
 * @returns {string} 主机名
 */
function extractHost(url) {
    if (!url) return "";
    try {
        var match = url.match(/^https?:\/\/([^\/]+)/);
        return match ? match[1] : "";
    } catch (e) {
        return "";
    }
}

/**
 * @brief 构建Cookie字符串
 * @description 根据用户信息构建锐捷ePortal登录所需的Cookie
 * @param {Object} cookies - 包含用户名、密码等信息的对象
 * @param {string} cookies.username - 用户名
 * @param {string} cookies.password - 密码
 * @param {string} cookies.service - 服务类型
 * @param {string} cookies.jsessionid - Session ID
 * @returns {string} 格式化的Cookie字符串
 */
function buildCookieString(cookies) {
    if (!cookies || typeof cookies !== 'object') return "";
    
    var parts = [];
    
    parts.push("EPORTAL_COOKIE_DOMAIN=false");
    parts.push("EPORTAL_COOKIE_SAVEPASSWORD=true");
    parts.push("EPORTAL_COOKIE_OPERATORPWD=");
    parts.push("EPORTAL_COOKIE_NEWV=true");
    
    if (cookies.password) {
        parts.push("EPORTAL_COOKIE_PASSWORD=" + cookies.password);
    } else {
        parts.push("EPORTAL_COOKIE_PASSWORD=");
    }
    
    parts.push("EPORTAL_AUTO_LAND=");
    
    if (cookies.username) {
        parts.push("EPORTAL_COOKIE_USERNAME=" + cookies.username);
    }
    
    if (cookies.service) {
        var encodedService = encodeURIComponent(cookies.service);
        parts.push("EPORTAL_COOKIE_SERVER=" + encodedService);
        parts.push("EPORTAL_COOKIE_SERVER_NAME=" + encodedService);
    }
    
    parts.push("EPORTAL_USER_GROUP=Student");
    
    if (cookies.jsessionid) {
        parts.push("JSESSIONID=" + cookies.jsessionid);
    }
    
    return parts.join("; ");
}

/**
 * @brief 构建Referer头
 * @description 根据服务器IP、查询字符串和URL构建Referer字段
 * @param {string} serverIp - 服务器IP地址
 * @param {string} queryString - 查询字符串
 * @param {string} getUrl - 完整URL
 * @returns {string} Referer URL
 */
function buildReferer(serverIp, queryString, getUrl) {
    if (!serverIp) return "";
    
    var baseUrl = getUrl || serverIp;
    if (queryString) {
        baseUrl += "?" + queryString;
    }
    
    return baseUrl;
}

/**
 * @brief 保存Header到JSON文件
 * @description 将HTTP头对象序列化为JSON并保存到指定路径
 * @param {Object} header - HTTP头对象
 * @param {string} outputPath - 输出文件路径
 */
function saveHeaderToJson(header, outputPath) {
    var dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(outputPath, JSON.stringify(header, null, 4), 'utf8');
    log("Header 已保存到: " + outputPath);
}

/**
 * @brief 解析index URL
 * @description 解析锐捷ePortal的index URL，提取服务器IP、查询字符串、MAC地址等信息
 * @param {string} indexUrl - 登录页面的index URL
 * @returns {Object} 解析结果对象，包含serverIp、queryString、mac、getUrl
 */
function parseIndexUrl(indexUrl) {
    var result = {
        serverIp: "",
        queryString: "",
        mac: "",
        getUrl: ""
    };
    
    if (!indexUrl) return result;
    
    try {
        var urlMatch = indexUrl.match(/^(https?:\/\/[^\/]+)/);
        if (urlMatch) {
            result.serverIp = urlMatch[1];
        }
        
        var queryIndex = indexUrl.indexOf("?");
        if (queryIndex !== -1 && queryIndex < indexUrl.length - 1) {
            result.queryString = indexUrl.substring(queryIndex + 1);
        }
        
        if (queryIndex !== -1) {
            result.getUrl = indexUrl.substring(0, queryIndex);
        } else {
            result.getUrl = indexUrl;
        }
        
        var macMatch = result.queryString.match(/[?&]mac=([^&]+)/i);
        if (macMatch) {
            result.mac = decodeURIComponent(macMatch[1]);
        }
        
    } catch (e) {
        if (isDebug) console.error("解析 index_url 失败:", e);
    }
    
    return result;
}

if (typeof require !== 'undefined' && require.main === module) {
    var configPath = paths.config.path;
    var postDataPath = paths.postData.path;
    var outputPath = paths.postHeader.path;
    
    var config = {};
    var postData = {};
    
    log("=== 锐捷 ePortal POST Header 生成器 ===");
    log("");
    
    if (!fs.existsSync(configPath)) {
        console.error("错误: 配置文件不存在: " + configPath);
        process.exit(1);
    }
    
    try {
        var configData = fs.readFileSync(configPath, 'utf8');
        config = JSON.parse(configData);
        log("已加载配置文件: " + configPath);
    } catch (e) {
        console.error("读取配置文件失败:", e.message);
        process.exit(1);
    }
    
    if (fs.existsSync(postDataPath)) {
        try {
            var postDataContent = fs.readFileSync(postDataPath, 'utf8');
            postData = JSON.parse(postDataContent);
            log("已加载 POST 数据: " + postDataPath);
        } catch (e) {
            console.error("读取 POST 数据文件失败:", e.message);
        }
    }
    
    var indexUrl = config.index_url || "";
    if (!indexUrl) {
        console.error("错误: config.json 中缺少 index_url");
        process.exit(1);
    }
    
    var parsedIndex = parseIndexUrl(indexUrl);
    
    log("");
    log("解析 index_url 结果：");
    log("  服务器地址: " + parsedIndex.serverIp);
    log("  GET URL: " + parsedIndex.getUrl);
    log("  QueryString: " + (parsedIndex.queryString ? parsedIndex.queryString.substring(0, 60) + "..." : ""));
    log("  MAC: " + parsedIndex.mac);
    log("");
    
    var username = postData.userId || config.username || "";
    var password = postData.password || "";
    var service = postData.service || config.service || "";
    var serviceForCookie = service.includes('%') ? decodeURIComponent(service) : service;
    
    log("配置信息：");
    log("  用户名: " + username);
    log("  服务: " + service);
    log("");
    
    var contentLength = 0;
    if (bodyModule) {
        var postParams = {};
        
        if (username) postParams.username = username;
        if (config.password) postParams.password = config.password;
        if (config.RSA_exponent) postParams.exponent = config.RSA_exponent;
        if (config.RSA_modulus) postParams.modulus = config.RSA_modulus;
        if (service) postParams.service = service;
        if (postData.queryString) {
            postParams.queryString = postData.queryString;
        } else if (parsedIndex.queryString) {
            postParams.queryString = parsedIndex.queryString;
        }
        if (parsedIndex.mac) postParams.mac = parsedIndex.mac;
        
        var postDataResult = bodyModule.generateLoginPostData(postParams);
        contentLength = postDataResult.postData.length;
        log("自动计算的 Content-Length: " + contentLength);
    } else {
        console.error("错误: 无法加载 body.js 模块");
        process.exit(1);
    }
    
    log("");
    
    var header = generatePostHeader({
        serverIp: parsedIndex.serverIp,
        queryString: parsedIndex.queryString,
        getUrl: parsedIndex.getUrl,
        username: username,
        password: password,
        service: serviceForCookie,
        jsessionid: "",
        contentLength: contentLength,
        userAgent: "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36 Edg/140.0.0.0"
    });
    
    log("生成的 Header:");
    log(JSON.stringify(header, null, 4));
    
    saveHeaderToJson(header, outputPath);
    
    log("");
    log("完成！");
}

module.exports = {
    generatePostHeader: generatePostHeader,
    saveHeaderToJson: saveHeaderToJson,
    parseIndexUrl: parseIndexUrl
};