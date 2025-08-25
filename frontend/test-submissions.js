#!/usr/bin/env node

/**
 * Test runner script for Submissions feature
 * Runs comprehensive tests for the Content Submissions feature
 */

const { spawn } = require('child_process');
const path = require('path');

// Test configuration
const testConfigs = [
  {
    name: 'Submission API Service Tests',
    command: 'npm',
    args: ['test', '--', 'src/services/__tests__/submissionApi.test.ts'],
    description: 'Tests all submission API endpoints and service functions'
  },
  {
    name: 'Main Submissions Component Tests',
    command: 'npm',
    args: ['test', '--', 'src/pages/__tests__/Submissions.test.tsx'],
    description: 'Tests main component rendering, navigation, and basic interactions'
  },
  {
    name: 'Form Validation Tests',
    command: 'npm',
    args: ['test', '--', 'src/pages/__tests__/SubmissionFormValidation.test.tsx'],
    description: 'Tests Yup validation schema and form behavior'
  },
  {
    name: 'File Upload and Drag & Drop Tests',
    command: 'npm',
    args: ['test', '--', 'src/pages/__tests__/FileUpload.test.tsx'],
    description: 'Tests file handling, drag & drop, and upload functionality'
  },
  {
    name: 'URL Validation Tests',
    command: 'npm',
    args: ['test', '--', 'src/pages/__tests__/UrlValidation.test.tsx'],
    description: 'Tests URL processing, validation, and bulk entry'
  },
  {
    name: 'Error Handling and Edge Cases',
    command: 'npm',
    args: ['test', '--', 'src/pages/__tests__/ErrorHandling.test.tsx'],
    description: 'Tests error scenarios, network issues, and edge cases'
  },
  {
    name: 'Integration Workflow Tests',
    command: 'npm',
    args: ['test', '--', 'src/pages/__tests__/IntegrationWorkflows.test.tsx'],
    description: 'Tests complete end-to-end submission workflows'
  }
];

// Quick test suites for faster feedback
const quickTests = [
  {
    name: 'Quick Smoke Test',
    command: 'npm',
    args: ['test', '--', '--testNamePattern="should render|should handle basic"', 'src/pages/__tests__/Submissions.test.tsx'],
    description: 'Quick smoke tests for basic functionality'
  }
];

// Coverage test
const coverageTest = {
  name: 'Coverage Report',
  command: 'npm',
  args: ['run', 'test:coverage', '--', '--testPathPattern=Submissions|submission'],
  description: 'Generate coverage report for Submissions feature'
};

// Helper functions
function runCommand(config) {
  return new Promise((resolve, reject) => {
    console.log(`\n🧪 Running: ${config.name}`);
    console.log(`📝 ${config.description}`);
    console.log(`⚡ Command: ${config.command} ${config.args.join(' ')}\n`);
    
    const child = spawn(config.command, config.args, {
      stdio: 'inherit',
      shell: true,
      cwd: process.cwd()
    });
    
    child.on('close', (code) => {
      if (code === 0) {
        console.log(`✅ ${config.name} - PASSED\n`);
        resolve();
      } else {
        console.log(`❌ ${config.name} - FAILED (exit code: ${code})\n`);
        reject(new Error(`Test failed with exit code ${code}`));
      }
    });
    
    child.on('error', (error) => {
      console.log(`💥 ${config.name} - ERROR: ${error.message}\n`);
      reject(error);
    });
  });
}

async function runTestSuite(testSuite, suiteName) {
  console.log(`\n🚀 Starting ${suiteName}`);
  console.log('='.repeat(60));
  
  const results = {
    passed: 0,
    failed: 0,
    total: testSuite.length
  };
  
  for (const config of testSuite) {
    try {
      await runCommand(config);
      results.passed++;
    } catch (error) {
      results.failed++;
      console.error(`Error running ${config.name}:`, error.message);
    }
  }
  
  console.log(`\n📊 ${suiteName} Results:`);
  console.log(`✅ Passed: ${results.passed}`);
  console.log(`❌ Failed: ${results.failed}`);
  console.log(`📈 Total: ${results.total}`);
  console.log(`🎯 Success Rate: ${Math.round((results.passed / results.total) * 100)}%`);
  
  return results;
}

async function main() {
  const args = process.argv.slice(2);
  const mode = args[0] || 'full';
  
  console.log('🎯 Content Submissions Test Suite');
  console.log('==================================');
  console.log(`Mode: ${mode}`);
  console.log(`Working Directory: ${process.cwd()}`);
  
  try {
    let results;
    
    switch (mode) {
      case 'quick':
        results = await runTestSuite(quickTests, 'Quick Test Suite');
        break;
        
      case 'coverage':
        console.log('\n📊 Running Coverage Analysis...');
        results = await runCommand(coverageTest);
        break;
        
      case 'api':
        results = await runTestSuite([testConfigs[0]], 'API Tests Only');
        break;
        
      case 'component':
        results = await runTestSuite(testConfigs.slice(1, 3), 'Component Tests Only');
        break;
        
      case 'integration':
        results = await runTestSuite([testConfigs[6]], 'Integration Tests Only');
        break;
        
      case 'error':
        results = await runTestSuite([testConfigs[5]], 'Error Handling Tests Only');
        break;
        
      case 'full':
      default:
        results = await runTestSuite(testConfigs, 'Full Test Suite');
        
        if (results.failed === 0) {
          console.log('\n🎉 All tests passed! Running coverage report...');
          try {
            await runCommand(coverageTest);
          } catch (coverageError) {
            console.log('⚠️  Coverage report failed, but main tests passed');
          }
        }
        break;
    }
    
    if (typeof results === 'object' && results.failed > 0) {
      process.exit(1);
    }
    
    console.log('\n🎊 Test suite completed successfully!');
    console.log('\n💡 Usage examples:');
    console.log('  node test-submissions.js          # Run all tests');
    console.log('  node test-submissions.js quick    # Run quick smoke tests');
    console.log('  node test-submissions.js coverage # Run coverage report');
    console.log('  node test-submissions.js api      # Run API tests only');
    console.log('  node test-submissions.js component # Run component tests only');
    console.log('  node test-submissions.js integration # Run integration tests only');
    console.log('  node test-submissions.js error    # Run error handling tests only');
    
  } catch (error) {
    console.error('\n💥 Test suite failed:', error.message);
    process.exit(1);
  }
}

// Handle process termination gracefully
process.on('SIGINT', () => {
  console.log('\n\n⏹️  Test suite interrupted by user');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n\n⏹️  Test suite terminated');
  process.exit(0);
});

// Run the test suite
if (require.main === module) {
  main().catch((error) => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

module.exports = {
  runTestSuite,
  testConfigs,
  quickTests,
  coverageTest
};