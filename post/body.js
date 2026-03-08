/**
 * @file body.js
 * @author Aurorp1g
 * @brief 锐捷 ePortal 登录 POST 数据生成器
 * @description 用于生成校园网登录请求的POST数据，包含RSA加密、URL参数处理等功能
 */

var fs = require('fs');
var paths = require('./paths');

var DEBUG = false;
var args = process.argv.slice(2);
if (args.indexOf('--debug') !== -1) {
    DEBUG = true;
}

/**
 * @brief 调试日志输出函数
 * @description 仅在debug模式下输出日志到控制台
 */
function log() {
    if (DEBUG) {
        console.log.apply(console, arguments);
    }
}

/**
 * @brief 全局变量
 * @description 存储解析后的URL各部分信息
 */
var globalServerIp = "";
var globalQueryString = "";
var globalMac = "";
var globalGetUrl = "";

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
        console.error("解析 index_url 失败:", e);
    }
    
    globalServerIp = result.serverIp;
    globalQueryString = result.queryString;
    globalMac = result.mac;
    globalGetUrl = result.getUrl;
    
    return result;
}

/**
 * @brief RSA加密工具模块
 * @description 提供RSA大整数运算和加密功能，用于密码加密
 */
(function(global) {
    if (typeof global.RSAUtils === 'undefined')
        var RSAUtils = global.RSAUtils = {};

    var biRadixBits = 16;
    var bitsPerDigit = biRadixBits;
    var biRadix = 1 << 16;
    var biHalfRadix = biRadix >>> 1;
    var biRadixSquared = biRadix * biRadix;
    var maxDigitVal = biRadix - 1;
    var maxDigits;
    var ZERO_ARRAY;
    var bigZero, bigOne;

    var BigInt = global.BigInt = function(flag) {
        if (typeof flag == "boolean" && flag == true) {
            this.digits = null;
        } else {
            this.digits = ZERO_ARRAY.slice(0);
        }
        this.isNeg = false;
    };

    RSAUtils.setMaxDigits = function(value) {
        maxDigits = value;
        ZERO_ARRAY = new Array(maxDigits);
        for (var iza = 0; iza < ZERO_ARRAY.length; iza++) ZERO_ARRAY[iza] = 0;
        bigZero = new BigInt();
        bigOne = new BigInt();
        bigOne.digits[0] = 1;
    };
    RSAUtils.setMaxDigits(20);

    var dpl10 = 15;
    
    RSAUtils.biFromNumber = function(i) {
        var result = new BigInt();
        result.isNeg = i < 0;
        i = Math.abs(i);
        var j = 0;
        while (i > 0) {
            result.digits[j++] = i & maxDigitVal;
            i = Math.floor(i / biRadix);
        }
        return result;
    };

    var lr10 = RSAUtils.biFromNumber(1000000000000000);

    RSAUtils.biFromDecimal = function(s) {
        var isNeg = s.charAt(0) == '-';
        var i = isNeg ? 1 : 0;
        var result;
        while (i < s.length && s.charAt(i) == '0') ++i;
        if (i == s.length) {
            result = new BigInt();
        } else {
            var digitCount = s.length - i;
            var fgl = digitCount % dpl10;
            if (fgl == 0) fgl = dpl10;
            result = RSAUtils.biFromNumber(Number(s.substr(i, fgl)));
            i += fgl;
            while (i < s.length) {
                result = RSAUtils.biAdd(RSAUtils.biMultiply(result, lr10),
                        RSAUtils.biFromNumber(Number(s.substr(i, dpl10))));
                i += dpl10;
            }
            result.isNeg = isNeg;
        }
        return result;
    };

    RSAUtils.biCopy = function(bi) {
        var result = new BigInt(true);
        result.digits = bi.digits.slice(0);
        result.isNeg = bi.isNeg;
        return result;
    };

    RSAUtils.reverseStr = function(s) {
        var result = "";
        for (var i = s.length - 1; i > -1; --i) {
            result += s.charAt(i);
        }
        return result;
    };

    var hexatrigesimalToChar = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
        'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
        'u', 'v', 'w', 'x', 'y', 'z'
    ];

    RSAUtils.biToString = function(x, radix) {
        var b = new BigInt();
        b.digits[0] = radix;
        var qr = RSAUtils.biDivideModulo(x, b);
        var result = hexatrigesimalToChar[qr[1].digits[0]];
        while (RSAUtils.biCompare(qr[0], bigZero) == 1) {
            qr = RSAUtils.biDivideModulo(qr[0], b);
            result += hexatrigesimalToChar[qr[1].digits[0]];
        }
        return (x.isNeg ? "-" : "") + RSAUtils.reverseStr(result);
    };

    var hexToChar = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'a', 'b', 'c', 'd', 'e', 'f'];

    RSAUtils.digitToHex = function(n) {
        var mask = 0xf;
        var result = "";
        for (var i = 0; i < 4; ++i) {
            result += hexToChar[n & mask];
            n >>>= 4;
        }
        return RSAUtils.reverseStr(result);
    };

    RSAUtils.biToHex = function(x) {
        var result = "";
        var n = RSAUtils.biHighIndex(x);
        for (var i = RSAUtils.biHighIndex(x); i > -1; --i) {
            result += RSAUtils.digitToHex(x.digits[i]);
        }
        return result;
    };

    RSAUtils.charToHex = function(c) {
        var ZERO = 48;
        var NINE = ZERO + 9;
        var littleA = 97;
        var littleZ = littleA + 25;
        var bigA = 65;
        var bigZ = 65 + 25;
        var result;
        if (c >= ZERO && c <= NINE) {
            result = c - ZERO;
        } else if (c >= bigA && c <= bigZ) {
            result = 10 + c - bigA;
        } else if (c >= littleA && c <= littleZ) {
            result = 10 + c - littleA;
        } else {
            result = 0;
        }
        return result;
    };

    RSAUtils.hexToDigit = function(s) {
        var result = 0;
        var sl = Math.min(s.length, 4);
        for (var i = 0; i < sl; ++i) {
            result <<= 4;
            result |= RSAUtils.charToHex(s.charCodeAt(i));
        }
        return result;
    };

    RSAUtils.biFromHex = function(s) {
        var result = new BigInt();
        var sl = s.length;
        for (var i = sl, j = 0; i > 0; i -= 4, ++j) {
            result.digits[j] = RSAUtils.hexToDigit(s.substr(Math.max(i - 4, 0), Math.min(i, 4)));
        }
        return result;
    };

    RSAUtils.biAdd = function(x, y) {
        var result;
        if (x.isNeg != y.isNeg) {
            y.isNeg = !y.isNeg;
            result = RSAUtils.biSubtract(x, y);
            y.isNeg = !y.isNeg;
        } else {
            result = new BigInt();
            var c = 0;
            var n;
            for (var i = 0; i < x.digits.length; ++i) {
                n = x.digits[i] + y.digits[i] + c;
                result.digits[i] = n % biRadix;
                c = Number(n >= biRadix);
            }
            result.isNeg = x.isNeg;
        }
        return result;
    };

    RSAUtils.biSubtract = function(x, y) {
        var result;
        if (x.isNeg != y.isNeg) {
            y.isNeg = !y.isNeg;
            result = RSAUtils.biAdd(x, y);
            y.isNeg = !y.isNeg;
        } else {
            result = new BigInt();
            var n, c;
            c = 0;
            for (var i = 0; i < x.digits.length; ++i) {
                n = x.digits[i] - y.digits[i] + c;
                result.digits[i] = n % biRadix;
                if (result.digits[i] < 0) result.digits[i] += biRadix;
                c = 0 - Number(n < 0);
            }
            if (c == -1) {
                c = 0;
                for (var i = 0; i < x.digits.length; ++i) {
                    n = 0 - result.digits[i] + c;
                    result.digits[i] = n % biRadix;
                    if (result.digits[i] < 0) result.digits[i] += biRadix;
                    c = 0 - Number(n < 0);
                }
                result.isNeg = !x.isNeg;
            } else {
                result.isNeg = x.isNeg;
            }
        }
        return result;
    };

    RSAUtils.biHighIndex = function(x) {
        var result = x.digits.length - 1;
        while (result > 0 && x.digits[result] == 0) --result;
        return result;
    };

    RSAUtils.biNumBits = function(x) {
        var n = RSAUtils.biHighIndex(x);
        var d = x.digits[n];
        var m = (n + 1) * bitsPerDigit;
        var result;
        for (result = m; result > m - bitsPerDigit; --result) {
            if ((d & 0x8000) != 0) break;
            d <<= 1;
        }
        return result;
    };

    RSAUtils.biMultiply = function(x, y) {
        var result = new BigInt();
        var c;
        var n = RSAUtils.biHighIndex(x);
        var t = RSAUtils.biHighIndex(y);
        var u, uv, k;
        for (var i = 0; i <= t; ++i) {
            c = 0;
            k = i;
            for (var j = 0; j <= n; ++j, ++k) {
                uv = result.digits[k] + x.digits[j] * y.digits[i] + c;
                result.digits[k] = uv & maxDigitVal;
                c = uv >>> biRadixBits;
            }
            result.digits[i + n + 1] = c;
        }
        result.isNeg = x.isNeg != y.isNeg;
        return result;
    };

    RSAUtils.biMultiplyDigit = function(x, y) {
        var n, c, uv;
        var result = new BigInt();
        n = RSAUtils.biHighIndex(x);
        c = 0;
        for (var j = 0; j <= n; ++j) {
            uv = result.digits[j] + x.digits[j] * y + c;
            result.digits[j] = uv & maxDigitVal;
            c = uv >>> biRadixBits;
        }
        result.digits[1 + n] = c;
        return result;
    };

    RSAUtils.arrayCopy = function(src, srcStart, dest, destStart, n) {
        var m = Math.min(srcStart + n, src.length);
        for (var i = srcStart, j = destStart; i < m; ++i, ++j) {
            dest[j] = src[i];
        }
    };

    var highBitMasks = [0x0000, 0x8000, 0xC000, 0xE000, 0xF000, 0xF800,
            0xFC00, 0xFE00, 0xFF00, 0xFF80, 0xFFC0, 0xFFE0,
            0xFFF0, 0xFFF8, 0xFFFC, 0xFFFE, 0xFFFF];

    RSAUtils.biShiftLeft = function(x, n) {
        var digitCount = Math.floor(n / bitsPerDigit);
        var result = new BigInt();
        RSAUtils.arrayCopy(x.digits, 0, result.digits, digitCount,
                  result.digits.length - digitCount);
        var bits = n % bitsPerDigit;
        var rightBits = bitsPerDigit - bits;
        for (var i = result.digits.length - 1, i1 = i - 1; i > 0; --i, --i1) {
            result.digits[i] = ((result.digits[i] << bits) & maxDigitVal) |
                               ((result.digits[i1] & highBitMasks[bits]) >>>
                                (rightBits));
        }
        result.digits[0] = ((result.digits[i] << bits) & maxDigitVal);
        result.isNeg = x.isNeg;
        return result;
    };

    var lowBitMasks = [0x0000, 0x0001, 0x0003, 0x0007, 0x000F, 0x001F,
            0x003F, 0x007F, 0x00FF, 0x01FF, 0x03FF, 0x07FF,
            0x0FFF, 0x1FFF, 0x3FFF, 0x7FFF, 0xFFFF];

    RSAUtils.biShiftRight = function(x, n) {
        var digitCount = Math.floor(n / bitsPerDigit);
        var result = new BigInt();
        RSAUtils.arrayCopy(x.digits, digitCount, result.digits, 0,
                  x.digits.length - digitCount);
        var bits = n % bitsPerDigit;
        var leftBits = bitsPerDigit - bits;
        for (var i = 0, i1 = i + 1; i < result.digits.length - 1; ++i, ++i1) {
            result.digits[i] = (result.digits[i] >>> bits) |
                               ((result.digits[i1] & lowBitMasks[bits]) << leftBits);
        }
        result.digits[result.digits.length - 1] >>>= bits;
        result.isNeg = x.isNeg;
        return result;
    };

    RSAUtils.biMultiplyByRadixPower = function(x, n) {
        var result = new BigInt();
        RSAUtils.arrayCopy(x.digits, 0, result.digits, n, result.digits.length - n);
        return result;
    };

    RSAUtils.biDivideByRadixPower = function(x, n) {
        var result = new BigInt();
        RSAUtils.arrayCopy(x.digits, n, result.digits, 0, result.digits.length - n);
        return result;
    };

    RSAUtils.biModuloByRadixPower = function(x, n) {
        var result = new BigInt();
        RSAUtils.arrayCopy(x.digits, 0, result.digits, 0, n);
        return result;
    };

    RSAUtils.biCompare = function(x, y) {
        if (x.isNeg != y.isNeg) {
            return 1 - 2 * Number(x.isNeg);
        }
        for (var i = x.digits.length - 1; i >= 0; --i) {
            if (x.digits[i] != y.digits[i]) {
                if (x.isNeg) {
                    return 1 - 2 * Number(x.digits[i] > y.digits[i]);
                } else {
                    return 1 - 2 * Number(x.digits[i] < y.digits[i]);
                }
            }
        }
        return 0;
    };

    RSAUtils.biDivideModulo = function(x, y) {
        var nb = RSAUtils.biNumBits(x);
        var tb = RSAUtils.biNumBits(y);
        var origYIsNeg = y.isNeg;
        var q, r;
        if (nb < tb) {
            if (x.isNeg) {
                q = RSAUtils.biCopy(bigOne);
                q.isNeg = !y.isNeg;
                x.isNeg = false;
                y.isNeg = false;
                r = RSAUtils.biSubtract(y, x);
                x.isNeg = true;
                y.isNeg = origYIsNeg;
            } else {
                q = new BigInt();
                r = RSAUtils.biCopy(x);
            }
            return [q, r];
        }

        q = new BigInt();
        r = x;

        var t = Math.ceil(tb / bitsPerDigit) - 1;
        var lambda = 0;
        while (y.digits[t] < biHalfRadix) {
            y = RSAUtils.biShiftLeft(y, 1);
            ++lambda;
            ++tb;
            t = Math.ceil(tb / bitsPerDigit) - 1;
        }
        r = RSAUtils.biShiftLeft(r, lambda);
        nb += lambda;
        var n = Math.ceil(nb / bitsPerDigit) - 1;

        var b = RSAUtils.biMultiplyByRadixPower(y, n - t);
        while (RSAUtils.biCompare(r, b) != -1) {
            ++q.digits[n - t];
            r = RSAUtils.biSubtract(r, b);
        }
        for (var i = n; i > t; --i) {
            var ri = (i >= r.digits.length) ? 0 : r.digits[i];
            var ri1 = (i - 1 >= r.digits.length) ? 0 : r.digits[i - 1];
            var ri2 = (i - 2 >= r.digits.length) ? 0 : r.digits[i - 2];
            var yt = (t >= y.digits.length) ? 0 : y.digits[t];
            var yt1 = (t - 1 >= y.digits.length) ? 0 : y.digits[t - 1];
            if (ri == yt) {
                q.digits[i - t - 1] = maxDigitVal;
            } else {
                q.digits[i - t - 1] = Math.floor((ri * biRadix + ri1) / yt);
            }

            var c1 = q.digits[i - t - 1] * ((yt * biRadix) + yt1);
            var c2 = (ri * biRadixSquared) + ((ri1 * biRadix) + ri2);
            while (c1 > c2) {
                --q.digits[i - t - 1];
                c1 = q.digits[i - t - 1] * ((yt * biRadix) | yt1);
                c2 = (ri * biRadix * biRadix) + ((ri1 * biRadix) + ri2);
            }

            b = RSAUtils.biMultiplyByRadixPower(y, i - t - 1);
            r = RSAUtils.biSubtract(r, RSAUtils.biMultiplyDigit(b, q.digits[i - t - 1]));
            if (r.isNeg) {
                r = RSAUtils.biAdd(r, b);
                --q.digits[i - t - 1];
            }
        }
        r = RSAUtils.biShiftRight(r, lambda);
        q.isNeg = x.isNeg != origYIsNeg;
        if (x.isNeg) {
            if (origYIsNeg) {
                q = RSAUtils.biAdd(q, bigOne);
            } else {
                q = RSAUtils.biSubtract(q, bigOne);
            }
            y = RSAUtils.biShiftRight(y, lambda);
            r = RSAUtils.biSubtract(y, r);
        }
        if (r.digits[0] == 0 && RSAUtils.biHighIndex(r) == 0) r.isNeg = false;

        return [q, r];
    };

    RSAUtils.biDivide = function(x, y) {
        return RSAUtils.biDivideModulo(x, y)[0];
    };

    RSAUtils.biModulo = function(x, y) {
        return RSAUtils.biDivideModulo(x, y)[1];
    };

    RSAUtils.biMultiplyMod = function(x, y, m) {
        return RSAUtils.biModulo(RSAUtils.biMultiply(x, y), m);
    };

    RSAUtils.biPow = function(x, y) {
        var result = bigOne;
        var a = x;
        while (true) {
            if ((y & 1) != 0) result = RSAUtils.biMultiply(result, a);
            y >>= 1;
            if (y == 0) break;
            a = RSAUtils.biMultiply(a, a);
        }
        return result;
    };

    RSAUtils.biPowMod = function(x, y, m) {
        var result = bigOne;
        var a = x;
        var k = y;
        while (true) {
            if ((k.digits[0] & 1) != 0) result = RSAUtils.biMultiplyMod(result, a, m);
            k = RSAUtils.biShiftRight(k, 1);
            if (k.digits[0] == 0 && RSAUtils.biHighIndex(k) == 0) break;
            a = RSAUtils.biMultiplyMod(a, a, m);
        }
        return result;
    };

    global.BarrettMu = function(m) {
        this.modulus = RSAUtils.biCopy(m);
        this.k = RSAUtils.biHighIndex(this.modulus) + 1;
        var b2k = new BigInt();
        b2k.digits[2 * this.k] = 1;
        this.mu = RSAUtils.biDivide(b2k, this.modulus);
        this.bkplus1 = new BigInt();
        this.bkplus1.digits[this.k + 1] = 1;
        this.modulo = BarrettMu_modulo;
        this.multiplyMod = BarrettMu_multiplyMod;
        this.powMod = BarrettMu_powMod;
    };

    function BarrettMu_modulo(x) {
        var $dmath = RSAUtils;
        var q1 = $dmath.biDivideByRadixPower(x, this.k - 1);
        var q2 = $dmath.biMultiply(q1, this.mu);
        var q3 = $dmath.biDivideByRadixPower(q2, this.k + 1);
        var r1 = $dmath.biModuloByRadixPower(x, this.k + 1);
        var r2term = $dmath.biMultiply(q3, this.modulus);
        var r2 = $dmath.biModuloByRadixPower(r2term, this.k + 1);
        var r = $dmath.biSubtract(r1, r2);
        if (r.isNeg) {
            r = $dmath.biAdd(r, this.bkplus1);
        }
        var rgtem = $dmath.biCompare(r, this.modulus) >= 0;
        while (rgtem) {
            r = $dmath.biSubtract(r, this.modulus);
            rgtem = $dmath.biCompare(r, this.modulus) >= 0;
        }
        return r;
    }

    function BarrettMu_multiplyMod(x, y) {
        var xy = RSAUtils.biMultiply(x, y);
        return this.modulo(xy);
    }

    function BarrettMu_powMod(x, y) {
        var result = new BigInt();
        result.digits[0] = 1;
        var a = x;
        var k = y;
        while (true) {
            if ((k.digits[0] & 1) != 0) result = this.multiplyMod(result, a);
            k = RSAUtils.biShiftRight(k, 1);
            if (k.digits[0] == 0 && RSAUtils.biHighIndex(k) == 0) break;
            a = this.multiplyMod(a, a);
        }
        return result;
    }

    var RSAKeyPair = function(encryptionExponent, decryptionExponent, modulus) {
        var $dmath = RSAUtils;
        this.e = $dmath.biFromHex(encryptionExponent);
        this.d = $dmath.biFromHex(decryptionExponent);
        this.m = $dmath.biFromHex(modulus);
        this.chunkSize = 2 * $dmath.biHighIndex(this.m);
        this.radix = 16;
        this.barrett = new global.BarrettMu(this.m);
    };

    RSAUtils.getKeyPair = function(encryptionExponent, decryptionExponent, modulus) {
        return new RSAKeyPair(encryptionExponent, decryptionExponent, modulus);
    };

    RSAUtils.encryptedString = function(key, s) {
        var a = [];
        var sl = s.length;
        var i = 0;
        while (i < sl) {
            a[i] = s.charCodeAt(i);
            i++;
        }

        while (a.length % key.chunkSize != 0) {
            a[i++] = 0;
        }

        var al = a.length;
        var result = "";
        var j, k, block;
        for (i = 0; i < al; i += key.chunkSize) {
            block = new BigInt();
            j = 0;
            for (k = i; k < i + key.chunkSize; ++j) {
                block.digits[j] = a[k++];
                block.digits[j] += a[k++] << 8;
            }
            var crypt = key.barrett.powMod(block, key.e);
            var text = key.radix == 16 ? RSAUtils.biToHex(crypt) : RSAUtils.biToString(crypt, key.radix);
            result += text + " ";
        }
        return result.substring(0, result.length - 1);
    };

    RSAUtils.setMaxDigits(130);

})(typeof global !== 'undefined' ? global : window);

/**
 * @brief 检查值是否为空
 * @description 判断对象是否为null、undefined或空字符串
 * @param {*} obj - 待检查的值
 * @returns {boolean} 如果为空返回true，否则返回false
 */
function isNull(obj) {
    return obj === undefined || obj === null || obj === '';
}

/**
 * @brief 双重URL编码
 * @description 对字符串进行两次URL编码，用于特殊场景
 * @param {string} str - 待编码的字符串
 * @returns {string} 双重编码后的字符串
 */
function doubleEncode(str) {
    return encodeURIComponent(encodeURIComponent(str));
}

/**
 * @brief 获取URL查询字符串
 * @description 从URL中提取查询字符串部分
 * @param {string} url - 输入的URL
 * @returns {string} 查询字符串部分
 */
function getQueryString(url) {
    if (!url) return "";
    var queryIndex = url.indexOf("?");
    if (queryIndex !== -1 && queryIndex < url.length - 1) {
        return url.substring(queryIndex + 1);
    }
    return "";
}

/**
 * @brief 根据参数名获取URL查询值
 * @description 从URL查询字符串中提取指定参数名的值
 * @param {string} url - 输入的URL
 * @param {string} name - 参数名
 * @returns {string} 参数值，如果不存在返回空字符串
 */
function getQueryStringByName(url, name) {
    var result = url.match(new RegExp("[\\?\\&]" + name + "=([^\\&]+)", "i"));
    if (result === null || result.length < 2) {
        return "";
    }
    return result[1];
}

/**
 * @brief 使用RSA加密密码
 * @description 对密码进行RSA加密处理，添加MAC地址前缀并反转后加密
 * @param {string} password - 明文密码
 * @param {string} publicKeyExponent - RSA公钥指数
 * @param {string} publicKeyModulus - RSA公钥模数
 * @param {string} macString - MAC地址字符串
 * @returns {string} RSA加密后的密码字符串
 */
function encryptedPassword(password, publicKeyExponent, publicKeyModulus, macString) {
    if (isNull(macString)) {
        macString = "111111111";
    }
    
    var passwordWithMac = password + ">" + macString;
    
    var reversed = passwordWithMac.split("").reverse().join("");
    
    RSAUtils.setMaxDigits(400);
    var key = RSAUtils.getKeyPair(publicKeyExponent, "", publicKeyModulus);
    return RSAUtils.encryptedString(key, reversed);
}

/**
 * @brief 生成登录POST数据
 * @description 根据参数生成锐捷ePortal登录所需的POST数据字符串
 * @param {Object} params - 登录参数对象
 * @param {string} params.username - 用户名
 * @param {string} params.password - 密码
 * @param {string} params.exponent - RSA公钥指数（默认10001）
 * @param {string} params.modulus - RSA公钥模数
 * @param {string} params.queryString - 查询字符串
 * @param {string} params.mac - MAC地址（默认111111111）
 * @param {string} params.service - 服务类型
 * @param {string} params.operatorUserId - 管理员用户ID
 * @param {string} params.operatorPwd - 管理员密码
 * @param {string} params.validCode - 验证码
 * @param {string} params.prefixValue - 用户名前缀
 * @param {boolean} params.passwordEncrypt - 是否加密密码（默认true）
 * @param {boolean} params.hasOperatorUserId - 是否包含管理员用户ID
 * @param {boolean} params.hasOperatorPwd - 是否包含管理员密码
 * @returns {Object} 包含postData、fields、raw的对象
 */
function generateLoginPostData(params) {
    var username = params.username || "";
    var password = params.password || "";
    var exponent = params.exponent || "10001";
    var modulus = params.modulus || "";
    var queryString = params.queryString || "";
    var mac = params.mac || "111111111";
    var service = params.service || "";
    var operatorUserId = params.operatorUserId || "";
    var operatorPwd = params.operatorPwd || "";
    var validCode = params.validCode || "";
    var prefixValue = params.prefixValue || "";
    var passwordEncrypt = params.passwordEncrypt !== false;
    var hasOperatorUserId = params.hasOperatorUserId || false;
    var hasOperatorPwd = params.hasOperatorPwd || false;

    var finalUsername = username;
    if (!isNull(prefixValue)) {
        finalUsername = prefixValue + username;
    }
    var userId = encodeURIComponent(finalUsername);

    var encryptedPwd;
    var encryptFlag = passwordEncrypt ? "true" : "false";
    
    if (passwordEncrypt) {
        if (password.length < 150) {
            var rawEncrypted = encryptedPassword(password, exponent, modulus, mac);
            encryptedPwd = encodeURIComponent(rawEncrypted);
        } else {
            encryptedPwd = encodeURIComponent(password);
        }
    } else {
        if (password.length > 150) {
            encryptFlag = "true";
        }
        encryptedPwd = encodeURIComponent(password);
    }
    var passwordEncryptEncoded = encodeURIComponent(encryptFlag);

    var serviceEncoded = "";
    if (!isNull(service)) {
        serviceEncoded = encodeURIComponent(service);
    }

    var queryStringEncoded = encodeURIComponent(queryString);

    var operatorPwdEncoded = "";
    if (hasOperatorPwd && !isNull(operatorPwd)) {
        if (passwordEncrypt && !isNull(operatorPwd)) {
            var rawOperatorEncrypted = encryptedPassword(operatorPwd, exponent, modulus, mac);
            operatorPwdEncoded = encodeURIComponent(rawOperatorEncrypted);
        } else {
            operatorPwdEncoded = encodeURIComponent(operatorPwd);
        }
    }

    var operatorUserIdEncoded = "";
    if (hasOperatorUserId && !isNull(operatorUserId)) {
        operatorUserIdEncoded = encodeURIComponent(operatorUserId);
    }

    var validcodeValue = validCode;

    var postData = "userId=" + userId + 
                   "&password=" + encryptedPwd + 
                   "&service=" + serviceEncoded + 
                   "&queryString=" + queryStringEncoded + 
                   "&operatorPwd=" + operatorPwdEncoded + 
                   "&operatorUserId=" + operatorUserIdEncoded + 
                   "&validcode=" + validcodeValue + 
                   "&passwordEncrypt=" + passwordEncryptEncoded;

    return {
        postData: postData,
        fields: {
            userId: userId,
            password: encryptedPwd,
            service: serviceEncoded,
            queryString: queryStringEncoded,
            operatorPwd: operatorPwdEncoded,
            operatorUserId: operatorUserIdEncoded,
            validcode: validcodeValue,
            passwordEncrypt: passwordEncryptEncoded
        },
        raw: {
            username: finalUsername,
            password: password,
            mac: mac,
            service: service,
            queryString: queryString
        }
    };
}

if (typeof require !== 'undefined' && require.main === module) {
    var configPath = paths.config.path;
    var postDataPath = paths.postData.path;
    var params = {};
    
    log("=== 锐捷 ePortal POST 数据生成器 ===");
    log("");
    
    if (!fs.existsSync(configPath)) {
        console.error("错误: 配置文件不存在: " + configPath);
        process.exit(1);
    }
    
    try {
        var configData = fs.readFileSync(configPath, 'utf8');
        var config = JSON.parse(configData);
        
        params.username = config.username;
        params.password = config.password;
        params.exponent = config.RSA_exponent;
        params.modulus = config.RSA_modulus;
        params.service = config.service;
        params.postUrl = config.post_url;
        
        if (config.index_url) {
            var parsed = parseIndexUrl(config.index_url);
            params.queryString = parsed.queryString;
            params.mac = parsed.mac;
            params.getUrl = parsed.getUrl;
        }
        
        log("已从配置文件加载参数: " + configPath);
        log("");
        log("解析结果：");
        log("  服务器地址: " + globalServerIp);
        log("  GET URL: " + globalGetUrl);
        log("  QueryString: " + globalQueryString.substring(0, 50) + "...");
        log("  MAC: " + globalMac);
        log("");
        
    } catch (e) {
        console.error("读取配置文件失败:", e.message);
        process.exit(1);
    }
    
    if (!params.username || !params.password || !params.exponent || !params.modulus) {
        console.error("错误: config.json 缺少必需参数 (username, password, RSA_exponent, RSA_modulus)");
        process.exit(1);
    }

    var result = generateLoginPostData(params);

    var dataDir = paths.postData.path.replace(/\/[^\/]+$/, '');
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
    }
    
    var orderedFields = {
        userId: result.fields.userId,
        password: result.fields.password,
        queryString: result.fields.queryString,
        passwordEncrypt: result.fields.passwordEncrypt,
        operatorPwd: result.fields.operatorPwd,
        operatorUserId: result.fields.operatorUserId,
        validcode: result.fields.validcode,
        service: result.fields.service
    };
    
    var jsonData = JSON.stringify(orderedFields, null, 4);
    
    fs.writeFileSync(postDataPath, jsonData, 'utf8');
    log("已将 POST 数据保存到：" + postDataPath);
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        generateLoginPostData,
        encryptedPassword,
        encodeURIComponent,
        isNull,
        getQueryString,
        getQueryStringByName,
        RSAUtils,
        parseIndexUrl,
        globalServerIp,
        globalQueryString,
        globalMac,
        globalGetUrl
    };
}