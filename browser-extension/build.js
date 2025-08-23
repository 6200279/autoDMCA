#!/usr/bin/env node
/**
 * Build Script for Content Protection Browser Extension
 * Packages extension for Chrome and Firefox distribution
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const EXTENSION_DIR = __dirname;
const BUILD_DIR = path.join(EXTENSION_DIR, 'dist');
const CHROME_DIR = path.join(EXTENSION_DIR, 'chrome');
const FIREFOX_DIR = path.join(EXTENSION_DIR, 'firefox');
const SHARED_DIR = path.join(EXTENSION_DIR, 'shared');
const ICONS_DIR = path.join(EXTENSION_DIR, 'icons');

// Utility functions
const ensureDir = (dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
};

const copyFile = (src, dest) => {
  fs.copyFileSync(src, dest);
  console.log(`Copied: ${path.relative(EXTENSION_DIR, src)} -> ${path.relative(EXTENSION_DIR, dest)}`);
};

const copyDir = (src, dest) => {
  ensureDir(dest);
  const files = fs.readdirSync(src);
  
  files.forEach(file => {
    const srcPath = path.join(src, file);
    const destPath = path.join(dest, file);
    
    if (fs.statSync(srcPath).isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      copyFile(srcPath, destPath);
    }
  });
};

// Build Chrome extension
const buildChrome = () => {
  console.log('\n📦 Building Chrome extension...');
  
  const chromeBuild = path.join(BUILD_DIR, 'chrome');
  ensureDir(chromeBuild);
  
  // Copy Chrome manifest
  copyFile(
    path.join(CHROME_DIR, 'manifest.json'),
    path.join(chromeBuild, 'manifest.json')
  );
  
  // Copy shared files
  copyDir(SHARED_DIR, path.join(chromeBuild, 'shared'));
  copyDir(ICONS_DIR, path.join(chromeBuild, 'icons'));
  
  // Copy README
  copyFile(
    path.join(EXTENSION_DIR, 'README.md'),
    path.join(chromeBuild, 'README.md')
  );
  
  console.log('✅ Chrome extension built successfully');
  return chromeBuild;
};

// Build Firefox extension
const buildFirefox = () => {
  console.log('\n🦊 Building Firefox extension...');
  
  const firefoxBuild = path.join(BUILD_DIR, 'firefox');
  ensureDir(firefoxBuild);
  
  // Copy Firefox manifest
  copyFile(
    path.join(FIREFOX_DIR, 'manifest.json'),
    path.join(firefoxBuild, 'manifest.json')
  );
  
  // Copy shared files
  copyDir(SHARED_DIR, path.join(firefoxBuild, 'shared'));
  copyDir(ICONS_DIR, path.join(firefoxBuild, 'icons'));
  
  // Copy README
  copyFile(
    path.join(EXTENSION_DIR, 'README.md'),
    path.join(firefoxBuild, 'README.md')
  );
  
  console.log('✅ Firefox extension built successfully');
  return firefoxBuild;
};

// Create ZIP packages
const createZipPackages = (chromeBuild, firefoxBuild) => {
  console.log('\n📦 Creating ZIP packages...');
  
  try {
    // Create Chrome ZIP
    const chromeZip = path.join(BUILD_DIR, 'content-protection-chrome.zip');
    execSync(`cd "${chromeBuild}" && zip -r "${chromeZip}" .`, { stdio: 'pipe' });
    console.log(`Created: ${path.relative(EXTENSION_DIR, chromeZip)}`);
    
    // Create Firefox ZIP  
    const firefoxZip = path.join(BUILD_DIR, 'content-protection-firefox.zip');
    execSync(`cd "${firefoxBuild}" && zip -r "${firefoxZip}" .`, { stdio: 'pipe' });
    console.log(`Created: ${path.relative(EXTENSION_DIR, firefoxZip)}`);
    
    console.log('✅ ZIP packages created successfully');
  } catch (error) {
    console.warn('⚠️  ZIP creation failed (zip command not available):');
    console.log('   You can manually create ZIP files from the dist/ directories');
  }
};

// Validate build
const validateBuild = () => {
  console.log('\n🔍 Validating build...');
  
  const requiredFiles = [
    'shared/background.js',
    'shared/firefox-background.js',
    'shared/content.js',
    'shared/content.css',
    'shared/popup.html',
    'shared/popup.js',
    'shared/utils.js',
    'icons/README.md'
  ];
  
  let allValid = true;
  
  ['chrome', 'firefox'].forEach(browser => {
    console.log(`\nChecking ${browser} build...`);
    const buildDir = path.join(BUILD_DIR, browser);
    
    // Check manifest
    const manifest = path.join(buildDir, 'manifest.json');
    if (fs.existsSync(manifest)) {
      console.log(`  ✅ manifest.json`);
    } else {
      console.log(`  ❌ manifest.json missing`);
      allValid = false;
    }
    
    // Check required files
    requiredFiles.forEach(file => {
      const filePath = path.join(buildDir, file);
      if (fs.existsSync(filePath)) {
        console.log(`  ✅ ${file}`);
      } else {
        console.log(`  ❌ ${file} missing`);
        allValid = false;
      }
    });
  });
  
  if (allValid) {
    console.log('\n✅ Build validation passed');
  } else {
    console.log('\n❌ Build validation failed');
    process.exit(1);
  }
};

// Clean build directory
const clean = () => {
  console.log('🧹 Cleaning build directory...');
  if (fs.existsSync(BUILD_DIR)) {
    fs.rmSync(BUILD_DIR, { recursive: true, force: true });
  }
  console.log('✅ Build directory cleaned');
};

// Main build function
const build = () => {
  console.log('🚀 Starting Content Protection Extension build...\n');
  
  // Clean previous builds
  clean();
  
  // Create build directory
  ensureDir(BUILD_DIR);
  
  // Build extensions
  const chromeBuild = buildChrome();
  const firefoxBuild = buildFirefox();
  
  // Validate builds
  validateBuild();
  
  // Create packages
  createZipPackages(chromeBuild, firefoxBuild);
  
  console.log('\n🎉 Build completed successfully!');
  console.log(`\nBuild outputs:`);
  console.log(`  Chrome: ${path.relative(EXTENSION_DIR, chromeBuild)}`);
  console.log(`  Firefox: ${path.relative(EXTENSION_DIR, firefoxBuild)}`);
  console.log(`  Packages: ${path.relative(EXTENSION_DIR, BUILD_DIR)}`);
  
  console.log('\n📝 Next steps:');
  console.log('  1. Test the built extensions in their respective browsers');
  console.log('  2. Create proper extension icons (see icons/README.md)');
  console.log('  3. Update API endpoints for production');
  console.log('  4. Submit to browser stores when ready');
};

// Handle command line arguments
const args = process.argv.slice(2);

if (args.includes('--clean')) {
  clean();
  process.exit(0);
}

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
Content Protection Extension Build Script

Usage:
  node build.js          Build extensions for both browsers
  node build.js --clean  Clean build directory
  node build.js --help   Show this help

Output:
  dist/chrome/          Chrome extension files
  dist/firefox/         Firefox extension files
  dist/*.zip           Packaged extensions (if zip available)
`);
  process.exit(0);
}

// Run build
build();