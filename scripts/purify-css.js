const purify = require('purify-css');
const fs = require('fs');
const path = require('path');

const htmlPath = path.join(__dirname, 'gui', 'index.html');
const outputCssPath = path.join(__dirname, 'gui', 'styles.css');
const cleanedCssPath = path.join(__dirname, 'gui', 'styles.cleaned.css');

const htmlContent = fs.readFileSync(htmlPath, 'utf8');

const styleRegex = /<style>([\s\S]*?)<\/style>/;
const match = htmlContent.match(styleRegex);

if (match) {
    const inlineCss = match[1];
    
    fs.writeFileSync(outputCssPath, inlineCss);
    console.log('✅ 已提取内联 CSS 到 styles.css');
    
    const pure = purify.default || purify;
    
    const result = pure(htmlContent, inlineCss, {
        minify: false,
        info: true
    });
    
    fs.writeFileSync(cleanedCssPath, result);
    
    const originalSize = inlineCss.length;
    const cleanedSize = result.length;
    const removed = originalSize - cleanedSize;
    const percent = ((removed / originalSize) * 100).toFixed(2);
    
    console.log('\n📊 清理结果:');
    console.log(`   原始大小: ${originalSize} 字节`);
    console.log(`   清理后: ${cleanedSize} 字节`);
    console.log(`   移除: ${removed} 字节 (${percent}%)`);
    console.log(`\n✅ 清理后的 CSS 已保存到: ${cleanedCssPath}`);
} else {
    console.log('❌ 未找到内联样式');
}