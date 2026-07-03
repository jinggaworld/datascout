const { ethers } = require('ethers');

// Step 1: Generate new wallet
const wallet = ethers.Wallet.createRandom();
console.log('=== New Agent Wallet ===');
console.log('Address:', wallet.address);
console.log('Private Key:', wallet.privateKey);

// Step 2: Try to register with CROO
async function register() {
  try {
    const sdk = require('@croo-network/sdk');
    console.log('\n=== CROO SDK loaded ===');
    console.log('Available exports:', Object.keys(sdk));
    
    // Try common SDK class names
    const AgentClient = sdk.AgentClient || sdk.Client || sdk.CrooClient || sdk.default;
    if (AgentClient) {
      console.log('Found client class:', AgentClient.name);
      const client = new AgentClient({
        apiUrl: 'https://api.croo.network',
        wsUrl: 'wss://api.croo.network/ws',
        privateKey: wallet.privateKey,
      });
      console.log('Client created, attempting registration...');
      
      if (typeof client.register === 'function') {
        const result = await client.register({
          name: 'DataScout',
          capability: 'dataset_search',
          description: 'Automated dataset search, scoring & reporting agent',
        });
        console.log('Registration result:', JSON.stringify(result, null, 2));
      } else {
        console.log('Client methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(client)));
      }
    } else {
      console.log('No client class found in SDK');
    }
  } catch (e) {
    console.log('SDK registration error:', e.message);
  }
}

register();
