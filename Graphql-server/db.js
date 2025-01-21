const { DataStore } = require('notarealdb');

// Create a DataStore instance pointing to the `data` directory
const store = new DataStore('./data');

module.exports = {
  locations: store.collection('locations'), // For the Locations table
  products: store.collection('products'), // For the Products table
  sales: store.collection('sales'), // For the Sales table
};
