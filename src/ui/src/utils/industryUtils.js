// Industry mapping from stored values to display labels
// Based on UK Standard Industrial Classification (SIC) codes
export const industryOptions = [
  { label: 'Select industry', value: '' },
  { label: 'Agriculture, Forestry and Fishing', value: 'agriculture' },
  { label: 'Mining and Quarrying', value: 'mining' },
  { label: 'Manufacturing', value: 'manufacturing' },
  { label: 'Electricity, Gas, Steam and Air Conditioning Supply', value: 'utilities' },
  { label: 'Construction', value: 'construction' },
  { label: 'Wholesale and Retail Trade', value: 'retail' },
  { label: 'Transportation and Storage', value: 'transport' },
  { label: 'Accommodation and Food Service Activities', value: 'accommodation' },
  { label: 'Information and Communication', value: 'information' },
  { label: 'Financial and Insurance Activities', value: 'financial' },
  { label: 'Real Estate Activities', value: 'real-estate' },
  { label: 'Professional, Scientific and Technical Activities', value: 'professional' },
  { label: 'Administrative and Support Service Activities', value: 'administrative' },
  { label: 'Public Administration and Defence', value: 'public-admin' },
  { label: 'Education', value: 'education' },
  { label: 'Human Health and Social Work Activities', value: 'health' },
  { label: 'Arts, Entertainment and Recreation', value: 'arts' },
  { label: 'Other Service Activities', value: 'other-services' }
];

/**
 * Get the proper display name for an industry value
 * @param {string} industryValue - The stored industry value (e.g., 'agriculture')
 * @returns {string} - The proper display name (e.g., 'Agriculture, Forestry and Fishing')
 */
export const getIndustryDisplayName = (industryValue) => {
  if (!industryValue) return 'Not specified';
  
  const industry = industryOptions.find(option => option.value === industryValue);
  return industry ? industry.label : industryValue.charAt(0).toUpperCase() + industryValue.slice(1);
};
