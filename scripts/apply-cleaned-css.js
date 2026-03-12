const fs = require('fs');
const path = require('path');

const htmlPath = path.join(__dirname, 'gui', 'index.html');
const cleanedCssPath = path.join(__dirname, 'gui', 'styles.cleaned.css');
const newHtmlPath = path.join(__dirname, 'gui', 'index.html');

const htmlContent = fs.readFileSync(htmlPath, 'utf8');
const cleanedCss = fs.readFileSync(cleanedCssPath, 'utf8');

const newHtml = htmlContent.replace(
    /<style>[\s\S]*?<\/style>/,
    `<style>\n${cleanedCss}\n</style>`
);

fs.writeFileSync(newHtmlPath, newHtml);

console.log('✅ 已将清理后的 CSS 替换回 index.html');

const originalSize = htmlContent.length;
const newSize = newHtml.length;
const saved = originalSize - newSize;

console.log('\n📊 HTML 文件变化:');
console.log(`   原始大小: ${originalSize} 字节`);
console.log(`   更新后: ${newSize} 字节`);
console.log(`   节省: ${saved} 字节`);