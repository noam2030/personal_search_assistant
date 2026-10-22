import { initializeApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  User,
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'AIzaSyB1b70BteUvUs3kYPrMD1aP-SxpqFbEz7M',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'ai-learning-499409.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'ai-learning-499409',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'ai-learning-499409.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '289332143182',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:289332143182:web:6931887c04f865c96c0f1f',
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

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
  const credential = await signInWithPopup(auth, googleProvider);
  return resolveAuthUserState(credential.user);
}

export async function signOutUser(): Promise<void> {
  await signOut(auth);
}

export function subscribeToAuthChanges(callback: (state: AuthUserState) => void): () => void {
  return onAuthStateChanged(auth, (user) => {
    callback(resolveAuthUserState(user));
  });
}
