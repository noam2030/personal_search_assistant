import { initializeApp, FirebaseApp } from 'firebase/app';
import {
  getAuth,
  Auth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  User,
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
};

let app: FirebaseApp | null = null;
export let auth: Auth | null = null;
const googleProvider = new GoogleAuthProvider();

if (firebaseConfig.apiKey && firebaseConfig.projectId) {
  app = initializeApp(firebaseConfig);
  auth = getAuth(app);
}

export const GUEST_USER_ID = 'guest';

export interface AuthUserState {
  userId: string;
  displayName: string;
  email: string | null;
  isGuest: boolean;
}

export function resolveAuthUserState(user: User | null): AuthUserState {
  if (!user) {
    return {
      userId: GUEST_USER_ID,
      displayName: 'Guest',
      email: null,
      isGuest: true,
    };
  }

  const userId = (user.email || user.uid || GUEST_USER_ID).trim();
  const displayName = (user.displayName || user.email || 'User').trim();
  return {
    userId,
    displayName,
    email: user.email,
    isGuest: false,
  };
}

export async function signInWithGoogle(): Promise<AuthUserState> {
  if (!auth) {
    throw new Error('Firebase Auth is not configured. Missing VITE_FIREBASE_API_KEY environment variable.');
  }
  const credential = await signInWithPopup(auth, googleProvider);
  return resolveAuthUserState(credential.user);
}

export async function signOutUser(): Promise<void> {
  if (auth) {
    await signOut(auth);
  }
}

export function subscribeToAuthChanges(callback: (state: AuthUserState) => void): () => void {
  if (!auth) {
    callback(resolveAuthUserState(null));
    return () => {};
  }
  return onAuthStateChanged(auth, (user) => {
    callback(resolveAuthUserState(user));
  });
}
