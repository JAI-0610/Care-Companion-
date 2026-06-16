const fs = require('fs');
const path = require('path');

// Create directory structure
const directories = [
  'src/components/common',
  'src/components/chat',
  'src/components/auth',
  'src/components/medications',
  'src/pages',
  'src/services',
  'src/hooks',
  'src/context',
  'src/utils',
  'src/styles',
  'public'
];

directories.forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`Created directory: ${dir}`);
  }
});

console.log('Project structure created successfully!');
console.log('\nNext steps:');
console.log('1. Run: npm install');
console.log('2. Run: npm run dev');