// Utility helpers for working with source document storage locations
// Keep logic centralized so the drawers stay lean and consistent
const stripLeadingSlash = (value = '') => value.replace(/^\/+/, '');

const sanitizeBucket = (bucket) => {
  if (!bucket) return null;
  return bucket.replace(/^s3:\/\//, '').replace(/\/+$/, '');
};

export const extractS3KeyFromUri = (uri) => {
  if (!uri || typeof uri !== 'string') {
    return null;
  }

  if (uri.startsWith('NEEDS_BUCKET:')) {
    return stripLeadingSlash(uri.replace('NEEDS_BUCKET:', '')) || null;
  }

  if (uri.startsWith('s3://')) {
    const withoutProtocol = uri.slice(5);
    const slashIndex = withoutProtocol.indexOf('/');
    if (slashIndex === -1) {
      return '';
    }
    return stripLeadingSlash(withoutProtocol.slice(slashIndex + 1));
  }

  try {
    const parsed = new URL(uri);
    return stripLeadingSlash(parsed.pathname || '') || null;
  } catch (error) {
    return null;
  }
};

export const resolveDocumentKey = ({ s3Path, s3Uri, documentId } = {}) => {
  if (s3Path) {
    return stripLeadingSlash(s3Path);
  }

  const keyFromUri = extractS3KeyFromUri(s3Uri);
  if (keyFromUri) {
    return keyFromUri;
  }

  if (documentId) {
    return stripLeadingSlash(documentId);
  }

  return null;
};

export const buildPageImageUri = ({ outputBucket, documentKey, pageNumber }) => {
  if (!outputBucket || !documentKey || !pageNumber) {
    return null;
  }

  const bucket = sanitizeBucket(outputBucket);
  if (!bucket) {
    return null;
  }

  const normalizedKey = stripLeadingSlash(documentKey);
  const normalizedPage = pageNumber.toString().trim();
  return `s3://${bucket}/${normalizedKey}/pages/${normalizedPage}/image.jpg`;
};

const coerceNumber = (value) => {
  if (value === null || value === undefined) {
    return null;
  }

  const parsed = Number(value);
  if (!Number.isNaN(parsed)) {
    return parsed;
  }

  const digits = value.toString().match(/\d+/g);
  if (!digits) {
    return null;
  }
  const lastGroup = digits[digits.length - 1];
  const parsedDigits = Number(lastGroup);
  return Number.isNaN(parsedDigits) ? null : parsedDigits;
};

export const getPageImageFromDocuments = ({ documents = [], documentKeyCandidates = [], pageNumber }) => {
  if (!documents.length || !documentKeyCandidates.length) {
    return null;
  }

  const keys = documentKeyCandidates.filter(Boolean);
  if (!keys.length) {
    return null;
  }

  const matchingDocument = documents.find((doc) => keys.includes(doc?.objectKey));
  if (!matchingDocument || !matchingDocument.pages || matchingDocument.pages.length === 0) {
    return null;
  }

  if (!pageNumber) {
    return matchingDocument.pages[0]?.ImageUri || null;
  }

  const numericTarget = coerceNumber(pageNumber);
  if (numericTarget && numericTarget > 0) {
    const byIndex = matchingDocument.pages[numericTarget - 1];
    if (byIndex?.ImageUri) {
      return byIndex.ImageUri;
    }
  }

  const normalizedTarget = pageNumber.toString().trim();
  const explicitMatch = matchingDocument.pages.find((page) => {
    const normalizedId = page?.Id ? page.Id.toString().trim() : '';
    if (normalizedId && normalizedId === normalizedTarget) {
      return true;
    }
    const numericId = coerceNumber(page?.Id ?? page?.PageNumber);
    return numericTarget && numericId && numericId === numericTarget;
  });

  if (explicitMatch?.ImageUri) {
    return explicitMatch.ImageUri;
  }

  return matchingDocument.pages[0]?.ImageUri || null;
};
