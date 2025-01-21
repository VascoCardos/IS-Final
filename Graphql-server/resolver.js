const db = require('./db');

const Query = {

  // Query all locations
  locations: () => db.locations.list(),

  // Query a single location by ID
  location: (root, args) => {
    return db.locations.get(args.id);
  },

  // Query all products
  products: () => db.products.list(),

  // Query a single product by ID
  product: (root, args) => {
    return db.products.get(args.id);
  },

  // Query all sales
  sales: () => db.sales.list(),

  // Query a single sale by ID
  sale: (root, args) => {
    return db.sales.get(args.id);
  }
};

const Location = {
  sales: (root) => {
    return db.sales.list().filter(sale => sale.location_id === root.id);
  }
};

const Product = {
  sales: (root) => {
    return db.sales.list().filter(sale => sale.product_id === root.id);
  }
};

const Sale = {
  product: (root) => {
    return db.products.get(root.product_id);
  },
  location: (root) => {
    return db.locations.get(root.location_id);
  }
};

const Mutation = {
  // Create a new location
  addLocation: (root, args) => {
    return db.locations.create({
      country: args.country,
      state: args.state,
      latitude: args.latitude,
      longitude: args.longitude
    });
  },

  // Create a new product
  addProduct: (root, args) => {
    return db.products.create({
      name: args.name,
      category: args.category,
      sub_category: args.sub_category,
      unit_cost: args.unit_cost,
      unit_price: args.unit_price
    });
  },

  // Create a new sale
  addSale: (root, args) => {
    return db.sales.create({
      product_id: args.product_id,
      location_id: args.location_id,
      sale_date: args.sale_date,
      customer_age: args.customer_age,
      customer_gender: args.customer_gender,
      order_quantity: args.order_quantity,
      profit: args.profit,
      cost: args.cost,
      revenue: args.revenue
    });
  }
};

module.exports = { Query, Location, Product, Sale, Mutation };
