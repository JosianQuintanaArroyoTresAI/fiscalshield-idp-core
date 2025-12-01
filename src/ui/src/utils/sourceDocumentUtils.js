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
  return `s3://${bucket}/${normalizedKey}/pages/${pageNumber}/image.jpg`;
};
